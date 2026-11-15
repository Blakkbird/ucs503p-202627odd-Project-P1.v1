"""Baselines, and a walk-forward backtest of the correction.

Everything the project claims has to survive this file. The rule
is that a prediction for day D may only come from a model fitted
on days strictly before D -- no shuffled train/test split, because
the rows are a time series and shuffling would let the model see
its own future.

Run it with `python code/evaluate.py`. It prints a table and
writes data/metrics.json.
"""

import json
import math
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config
import features
from model import Ridge

# Fitting on twenty days and calling the result a model would be
# dishonest. The backtest only starts once this many usable rows
# are behind it.
MIN_TRAIN = 40

# Searched inside each fit, on a validation tail of the training
# window only, so the choice never sees the day being predicted.
# Runs further up than it used to. Fitting in log space shrinks
# the scale of the target, so the penalty that suits it is larger;
# with the old ceiling of 30 the search was picking the last entry
# in the grid every time, which is the sign of a grid that stops
# too early rather than of a well-chosen alpha.
ALPHA_GRID = [0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0, 300.0]

# The model is fitted on log1p(PM2.5) and mapped back afterwards.
# See the class docstring in model.py for why.
LOG_TARGET = True

# The likely range is the middle 80% of the backtest's own errors:
# four days in five should land inside it. Errors are taken in log
# space, from forecasts made out of sample, and separately for each
# season, because a November error is several times a July one.
# The range used to come from the fit's in-sample spread, which is
# narrower than the truth by construction: it held 15 of the first
# 27 live days against the four in five it was meant to.
RANGE_QUANTILES = (0.10, 0.90)

# Fewer errors than this in a season and its range borrows the
# whole year's errors instead.
MIN_ERRORS = 30

# CPCB National AQI breakpoints for 24-hour PM2.5, in ug/m3. The
# service is useful to a person only if it lands in the right
# band, so that gets measured alongside the raw error.
BANDS = [(30, "Good"), (60, "Satisfactory"), (90, "Moderate"),
         (120, "Poor"), (250, "Very Poor"), (float("inf"), "Severe")]


def band(value):
    return next(name for edge, name in BANDS if value <= edge)


def score(pairs):
    """MAE, RMSE, bias and correlation for (truth, prediction)."""
    pairs = [(a, b) for a, b in pairs if a is not None and b is not None]
    n = len(pairs)
    if not n:
        return None

    mae = sum(abs(a - b) for a, b in pairs) / n
    rmse = math.sqrt(sum((a - b) ** 2 for a, b in pairs) / n)
    bias = sum(b - a for a, b in pairs) / n
    hits = sum(1 for a, b in pairs if band(a) == band(b)) / n

    truth_mean = sum(a for a, _ in pairs) / n
    pred_mean = sum(b for _, b in pairs) / n
    cov = sum((a - truth_mean) * (b - pred_mean) for a, b in pairs)
    spread = (math.sqrt(sum((a - truth_mean) ** 2 for a, _ in pairs))
              * math.sqrt(sum((b - pred_mean) ** 2 for _, b in pairs)))

    return {
        "n": n,
        "mae": round(mae, 3),
        "rmse": round(rmse, 3),
        "bias": round(bias, 3),
        "band_hit_rate": round(hits, 3),
        "r": round(cov / spread, 3) if spread else None,
    }


def fit(train):
    """Fit on `train`, choosing alpha on its most recent fifth.

    The validation slice is the tail rather than a random subset:
    picking alpha on days scattered through the training period
    would tune against conditions the real model never gets to see
    in order.
    """
    x = [s.x for s in train]
    y = [s.y for s in train]
    names = train[0].names

    cut = int(len(train) * 0.8)
    if cut < 10 or len(train) - cut < 5:
        # Too short to split; fall back to the middle of the grid.
        return Ridge(1.0, names, LOG_TARGET).fit(x, y)

    best, best_mae = 1.0, None
    for alpha in ALPHA_GRID:
        try:
            trial = Ridge(alpha, names, LOG_TARGET).fit(x[:cut], y[:cut])
        except ValueError:
            continue
        # Scored on the real scale even when the fit is in logs,
        # because micrograms are what the project is judged on.
        got = score(list(zip(y[cut:], trial.predict(x[cut:]))))
        if got and (best_mae is None or got["mae"] < best_mae):
            best, best_mae = alpha, got["mae"]

    return Ridge(best, names, LOG_TARGET).fit(x, y)


def published(ready, target):
    """The rows a forecast for `target` could have learnt from.

    Not simply every row before the target day. A row only becomes
    training data once its own reading is published, and the
    freshest published reading is the one `target` was built from,
    `obs_age` days back. The days between that one and the target
    were still unknown when the forecast went out.

    For a long time this was ready[:i], every earlier row, which let
    each backtest step learn from the one or two days just before
    it. That is a leak, if a small one, and measured on the 2026
    record it was worth about 0.2 µg/m3 of MAE. The live forecast
    never had it: daily.csv simply does not hold those readings yet.
    """
    newest = target.day - timedelta(days=int(target.obs_age))
    return [s for s in ready if s.day <= newest]


def backtest(samples):
    """Walk forward one day at a time, refitting as we go."""
    ready = features.usable(samples)
    runs = []

    for i, target in enumerate(ready):
        train = published(ready[:i], target)
        if len(train) < MIN_TRAIN:
            continue
        try:
            model = fit(train)
        except ValueError as exc:
            print(f"  skipped {target.day}: {exc}")
            continue
        runs.append({
            "day": target.day,
            "truth": target.y,
            "model": model.predict_one(target.x),
            "alpha": model.alpha,
            "n_train": len(train),
            "trained_to": train[-1].day,
            "live": target.live,
        })

    return runs


def baselines(samples, days):
    """Reference predictions for the same days the model was scored on.

    Persistence appears twice on purpose. The textbook version uses
    yesterday's reading, which is the number quoted in the
    proposal. The operational version uses the freshest reading the
    feed had actually published by the time the forecast goes out,
    which is what a real user would get. The gap between them is
    the cost of the CPCB publication lag, and the model only has
    access to the second one.
    """
    by_day = {s.day: s for s in samples}
    rows = [by_day[d] for d in days if d in by_day]
    if not rows:
        return {}

    # Climatology has to be causal too: the mean of everything
    # observed before the day in question, not of the whole record.
    history, running = [], {}
    for s in samples:
        running[s.day] = (sum(history) / len(history)) if history else None
        if s.y is not None:
            history.append(s.y)

    return {
        "persistence": [(s.y, s.persistence) for s in rows],
        "persistence_operational": [(s.y, s.persistence_op) for s in rows],
        "climatology": [(s.y, running.get(s.day)) for s in rows],
        "raw_cams": [(s.y, math.expm1(s.x[s.names.index("cams_log")]))
                     for s in rows],
    }


def quantile(values, q):
    """The q-th quantile, interpolating between neighbours."""
    xs = sorted(values)
    if not xs:
        return None
    pos = (len(xs) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def season_of(day):
    return "burning" if day.month in config.BURNING_MONTHS else "calm"


def log_error(run):
    """How far off a run was, in the log space the model works in."""
    return math.log1p(run["truth"]) - math.log1p(run["model"])


def calibrate(runs):
    """The likely range's edges, per season, from out-of-sample errors.

    Returned as log-space offsets: the range for a forecast f is
    expm1(log1p(f) + low) to expm1(log1p(f) + high). Under a log
    target that range comes out lopsided, wider above than below,
    which is the right shape for a quantity that spikes upwards.
    """
    errors = {"calm": [], "burning": []}
    for r in runs:
        errors[season_of(r["day"])].append(log_error(r))
    everything = errors["calm"] + errors["burning"]
    out = {}
    for season, own in errors.items():
        pool = own if len(own) >= MIN_ERRORS else everything
        if len(pool) < MIN_ERRORS:
            continue
        out[season] = {"low": round(quantile(pool, RANGE_QUANTILES[0]), 4),
                       "high": round(quantile(pool, RANGE_QUANTILES[1]), 4),
                       "errors": len(pool)}
    return out


def coverage(runs):
    """How often the range held the truth, sized only from the past.

    Walks forward the way the range is used: each day's range comes
    from the errors of the days before it, never its own. Reported
    per season and overall, against the 80% it is sized for.
    """
    seen = {"calm": [], "burning": []}
    held = {"calm": [0, 0], "burning": [0, 0]}
    for r in sorted(runs, key=lambda r: r["day"]):
        season = season_of(r["day"])
        pool = seen[season]
        if len(pool) < MIN_ERRORS:
            pool = seen["calm"] + seen["burning"]
        err = log_error(r)
        if len(pool) >= MIN_ERRORS:
            low = quantile(pool, RANGE_QUANTILES[0])
            high = quantile(pool, RANGE_QUANTILES[1])
            held[season][0] += low <= err <= high
            held[season][1] += 1
        seen[season].append(err)
    out = {k: {"held": h, "days": n, "rate": round(h / n, 3) if n else None}
           for k, (h, n) in held.items()}
    h = sum(v[0] for v in held.values())
    n = sum(v[1] for v in held.values())
    out["overall"] = {"held": h, "days": n,
                      "rate": round(h / n, 3) if n else None}
    return out


def likely_range(point, calibration, burning):
    """Turn a forecast into its likely range, or None if not sized."""
    block = (calibration or {}).get("burning" if burning else "calm")
    if not block or point is None:
        return None
    centre = math.log1p(point)
    return [max(math.expm1(centre + block["low"]), 0.0),
            math.expm1(centre + block["high"])]


def horizon_report(rows, use_weather, horizon, age, runs=None):
    """One horizon's backtest, scored and calibrated.

    For the outlook. CAMS and the weather in the table are day-ahead
    values, so for days two and three this is a little kind to the
    model; their live record is the check. The reading and the fire
    count are moved back properly, which is the part that matters.
    """
    samples = features.build(rows, use_weather=use_weather, age=age,
                             horizon=horizon)
    if runs is None:
        runs = backtest(samples)
    if not runs:
        return None
    by_day = {s.day: s for s in samples}
    model = score([(r["truth"], r["model"]) for r in runs])
    ref = score([(r["truth"], by_day[r["day"]].persistence_op)
                 for r in runs])
    gain = (ref["mae"] - model["mae"]) / ref["mae"] if ref and \
        ref["mae"] else None
    return {
        "horizon": horizon,
        "age": age,
        "days": len(runs),
        "model": model,
        "persistence": ref,
        "skill": None if gain is None else round(gain, 4),
        "calibration": calibrate(runs),
        "coverage": coverage(runs),
    }


def season_split(runs):
    calm = [r for r in runs if r["day"].month not in config.BURNING_MONTHS]
    burn = [r for r in runs if r["day"].month in config.BURNING_MONTHS]
    return {"calm": calm, "burning": burn}


def breakdown(samples, subset):
    """The model and every baseline, scored on one subset of runs."""
    days = [r["day"] for r in subset]
    entry = {"model": score([(r["truth"], r["model"]) for r in subset])}
    for name, pairs in baselines(samples, days).items():
        entry[name] = score(pairs)
    return entry


def report(use_weather=True, age=None, rows=None):
    """The headline backtest, at one reading age.

    Left alone, `age` is config.OBS_REFERENCE_AGE: the freshness
    the feed actually delivers now. The model lab scores the other
    ages, so a slower feed shows up as a measured cost rather than
    a surprise.
    """
    age = features.default_age() if age is None else age
    samples = features.build(rows, use_weather=use_weather, age=age)
    runs = backtest(samples)
    if not runs:
        print(f"Not enough usable rows to backtest "
              f"(need more than {MIN_TRAIN}).")
        return None

    days = [r["day"] for r in runs]
    scored = {"model": score([(r["truth"], r["model"]) for r in runs])}
    for name, pairs in baselines(samples, days).items():
        scored[name] = score(pairs)

    out = {
        "generated_for": days[-1].isoformat(),
        "window": {"first": days[0].isoformat(), "last": days[-1].isoformat()},
        "features": samples[0].names,
        "obs_age": age,
        "log_target": LOG_TARGET,
        "min_train": MIN_TRAIN,
        "min_obs_hours": config.MIN_OBS_HOURS,
        "overall": scored,
        "by_season": {},
        "by_provenance": {},
        "skill": {},
    }

    # Two skill numbers, and the distinction matters enough that
    # neither is allowed to be the only one reported.
    #
    # The operational figure is the honest one. It compares the
    # model against the best a person could actually do at 08:00
    # with the data published by then, which is a reading roughly
    # four days old. That is the same information set the model
    # has, so it is a fair fight and it is what the service is
    # worth to a user.
    #
    # The textbook figure compares against yesterday's reading,
    # which nobody has yet when the forecast goes out. It is
    # reported anyway because it is the number quoted in the
    # proposal and because it bounds what any amount of modelling
    # could buy: closing that gap needs a faster feed, not a
    # better regression.
    for label, key in (("operational", "persistence_operational"),
                       ("textbook", "persistence")):
        ref = scored.get(key)
        if ref and scored["model"] and ref["mae"]:
            gain = (ref["mae"] - scored["model"]["mae"]) / ref["mae"]
            out["skill"][label] = round(gain, 4)

    # Kept under the old name so anything already reading the file
    # does not silently start seeing nothing.
    out["skill_vs_persistence"] = out["skill"].get("textbook")

    for season, subset in season_split(runs).items():
        if subset:
            out["by_season"][season] = breakdown(samples, subset)

    # The same scores split by where the inputs came from. Archive
    # rows read CAMS and weather from series stitched out of many
    # model runs, which are a little kinder than a real day-ahead
    # forecast. Live rows carry the forecast that was actually
    # issued, so they are the check on how much the archive
    # flatters the totals.
    for kind, live in (("live", True), ("backfilled", False)):
        subset = [r for r in runs if r["live"] == live]
        if subset:
            out["by_provenance"][kind] = breakdown(samples, subset)

    burning = [r for r in runs if r["day"].month in config.BURNING_MONTHS]
    out["counts"] = {
        "burning_live": sum(1 for r in burning if r["live"]),
        "burning_backfilled": sum(1 for r in burning if not r["live"]),
    }

    return out, runs


def write_backtest(out, runs, path=None):
    """data/backtest.json: one walk-forward forecast per scored day."""
    path = path or config.BACKTEST_JSON
    blob = {
        "window": out["window"],
        "runs": [{"date": r["day"].isoformat(),
                  "truth": round(r["truth"], 2),
                  "model": round(r["model"], 2),
                  "live": r["live"]} for r in runs],
    }
    with open(path, "w") as f:
        json.dump(blob, f, separators=(",", ":"))
    print(f"wrote {path} ({len(runs)} days)")


def ship(rows, use_weather=True, target=None):
    """Fit the model tomorrow's forecast will use, and save it.

    Fitted at the age of the freshest reading actually on file for
    tomorrow, which on a normal day is the reference age and on a
    slow one is older. Saved with that age, so predict.py and the
    dashboard can check they are holding the right one.
    """
    target = target or datetime.now(config.IST).date() + timedelta(days=1)
    age = (features.freshest_age(rows, target)
           or features.default_age())
    ready = features.usable(features.build(rows, use_weather=use_weather,
                                           age=age))
    if len(ready) <= MIN_TRAIN:
        return None
    final = fit(ready)
    save_model(final, age, config.MODEL_JSON, samples=ready)
    return final, age, len(ready)


# The plain readings a model is fitted on, by the name they have in
# a sample's raw readings. Wind direction is left out: it is a circle,
# and every bearing turns up in a year.
RANGE_INPUTS = ("cams", "obs_recent", "temp", "rh", "wind_speed", "fires")


def fitted_ranges(samples):
    """{reading: [lowest, highest]} over the rows a model was fitted on.

    Kept with the model so that anything asking it about other inputs
    (the API's what-if) can tell when it is being asked to extrapolate.
    A spread-based test is not enough: fires enter the model on a log
    scale, and six times the largest count ever seen is still well
    inside four standard deviations there.
    """
    out = {}
    for name in RANGE_INPUTS:
        values = [s.raw.get(name) for s in samples
                  if s.raw.get(name) is not None]
        if values:
            out[name] = [round(min(values), 2), round(max(values), 2)]
    return out


def save_model(model, age, path, horizon=1, samples=None):
    """model.json: the fitted weights, the reading age they were fitted
    at, and the range of every reading in the rows behind them."""
    blob = model.to_dict()
    blob["obs_age"] = age
    blob["horizon"] = horizon
    if samples:
        blob["ranges"] = fitted_ranges(samples)
    with open(path, "w") as f:
        json.dump(blob, f, indent=2)


def show(out, runs):
    print(f"\nBacktest {out['window']['first']} to {out['window']['last']}"
          f"  ({len(runs)} days, refit each day, readings "
          f"{out['obs_age']} days old)")
    print(f"Features: {', '.join(out['features'])}\n")

    head = f"{'':26s}{'n':>5s}{'MAE':>9s}{'RMSE':>9s}{'bias':>9s}{'band':>8s}"
    print(head)
    print("-" * len(head))
    for name in ("model", "persistence", "persistence_operational",
                 "climatology", "raw_cams"):
        got = out["overall"].get(name)
        if not got:
            continue
        print(f"{name:26s}{got['n']:5d}{got['mae']:9.2f}{got['rmse']:9.2f}"
              f"{got['bias']:9.2f}{got['band_hit_rate']:8.2f}")

    print()
    for label in ("operational", "textbook"):
        gain = out["skill"].get(label)
        if gain is None:
            continue
        verdict = "beats" if gain > 0 else "loses to"
        print(f"vs {label:12s} persistence: {verdict} it by "
              f"{abs(gain) * 100:5.1f}% MAE")
    print("(target: 10% calm, 20% burning season, against operational)")

    groups = list(out["by_season"].items())
    groups += list(out.get("by_provenance", {}).items())
    for label, entry in groups:
        if entry.get("model") and entry.get("persistence_operational"):
            m = entry["model"]["mae"]
            p = entry["persistence_operational"]["mae"]
            print(f"  {label:10s} n={entry['model']['n']:3d}  "
                  f"model {m:6.2f}  persistence_op {p:6.2f}  "
                  f"({(p - m) / p * 100:+.1f}%)")


def main():
    # Weather is on unless explicitly switched off. `--no-weather`
    # reproduces the pre-review model and is how the ablation
    # table in the report was generated.
    weather = "--no-weather" not in sys.argv
    rows = features.load()
    built = report(use_weather=weather, rows=rows)
    if built is None:
        return 1
    out, runs = built
    show(out, runs)

    # One block per horizon, at the ages tomorrow's forecast and the
    # outlook will actually use today. Each carries the range's
    # edges and how often a range sized like that held the truth.
    # The headline run is reused when the ages match, which they do
    # whenever the feed is on time.
    target = datetime.now(config.IST).date() + timedelta(days=1)
    age = features.freshest_age(rows, target) or features.default_age()
    out["horizons"] = {}
    for h in (1, *config.OUTLOOK_HORIZONS):
        at = age + h - 1
        reuse = runs if (h == 1 and at == out["obs_age"]) else None
        got = horizon_report(rows, weather, h, at, reuse)
        if got:
            out["horizons"][str(h)] = got
            cov = got["coverage"]["overall"]
            print(f"horizon {h} (age {at}): MAE {got['model']['mae']:.2f}, "
                  f"skill {got['skill'] * 100:+.1f}%, range held "
                  f"{cov['held']} of {cov['days']}")

    config.DATA.mkdir(exist_ok=True)
    with open(config.METRICS_JSON, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nwrote {config.METRICS_JSON}")

    # The day-by-day forecasts behind those totals. The dashboard
    # draws them under the live record, so its chart reaches back
    # through last year's burning season instead of starting in
    # September. Each one came from a model fitted only on the days
    # before it, the same as the totals.
    write_backtest(out, runs)

    # Ship a model fitted on the whole record, at the age tomorrow's
    # reading will actually have.
    shipped = ship(rows, use_weather=weather)
    if shipped:
        final, age, n = shipped
        print(f"wrote {config.MODEL_JSON} (alpha={final.alpha}, "
              f"fitted on {n} rows, readings {age} days old)")
        print("\nstandardised weights, strongest first:")
        for name, weight in final.weights():
            print(f"    {name:16s}{weight:+8.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
