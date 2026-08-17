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
ALPHA_GRID = [0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0]

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
        return Ridge(alpha=1.0, names=names).fit(x, y)

    best, best_mae = 1.0, None
    for alpha in ALPHA_GRID:
        try:
            trial = Ridge(alpha, names).fit(x[:cut], y[:cut])
        except ValueError:
            continue
        got = score(list(zip(y[cut:], trial.predict(x[cut:]))))
        if got and (best_mae is None or got["mae"] < best_mae):
            best, best_mae = alpha, got["mae"]

    return Ridge(best, names).fit(x, y)


def backtest(samples):
    """Walk forward one day at a time, refitting as we go."""
    ready = features.usable(samples)
    runs = []

    for i in range(MIN_TRAIN, len(ready)):
        train, target = ready[:i], ready[i]
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


def season_split(runs):
    calm = [r for r in runs if r["day"].month not in config.BURNING_MONTHS]
    burn = [r for r in runs if r["day"].month in config.BURNING_MONTHS]
    return {"calm": calm, "burning": burn}


def report(use_weather=False):
    samples = features.build(use_weather=use_weather)
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
        "min_train": MIN_TRAIN,
        "overall": scored,
        "by_season": {},
        "skill_vs_persistence": None,
    }

    persistence = scored.get("persistence")
    if persistence and scored["model"]:
        gain = (persistence["mae"] - scored["model"]["mae"]) / persistence["mae"]
        out["skill_vs_persistence"] = round(gain, 4)

    for season, subset in season_split(runs).items():
        if not subset:
            continue
        sub_days = [r["day"] for r in subset]
        entry = {"model": score([(r["truth"], r["model"]) for r in subset])}
        for name, pairs in baselines(samples, sub_days).items():
            entry[name] = score(pairs)
        out["by_season"][season] = entry

    return out, runs


def show(out, runs):
    print(f"\nBacktest {out['window']['first']} to {out['window']['last']}"
          f"  ({len(runs)} days, refit each day)")
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

    gain = out["skill_vs_persistence"]
    if gain is not None:
        verdict = "beats" if gain > 0 else "loses to"
        print(f"\nModel {verdict} persistence by {abs(gain) * 100:.1f}% MAE "
              f"(target: 10% calm, 20% burning season)")

    for season, entry in out["by_season"].items():
        if entry.get("model") and entry.get("persistence"):
            m, p = entry["model"]["mae"], entry["persistence"]["mae"]
            print(f"  {season:8s} n={entry['model']['n']:3d}  "
                  f"model {m:6.2f}  persistence {p:6.2f}  "
                  f"({(p - m) / p * 100:+.1f}%)")


def main():
    weather = "--weather" in sys.argv
    built = report(use_weather=weather)
    if built is None:
        return 1
    out, runs = built
    show(out, runs)

    config.DATA.mkdir(exist_ok=True)
    with open(config.METRICS_JSON, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nwrote {config.METRICS_JSON}")

    # Ship a model fitted on the whole record, ready for tomorrow.
    ready = features.usable(features.build(use_weather=weather))
    if len(ready) > MIN_TRAIN:
        final = fit(ready)
        final.save(config.MODEL_JSON)
        print(f"wrote {config.MODEL_JSON} "
              f"(alpha={final.alpha}, fitted on {len(ready)} rows)")
        print("\nstandardised weights, strongest first:")
        for name, weight in final.weights():
            print(f"    {name:16s}{weight:+8.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
