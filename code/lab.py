"""The model lab: every candidate, the same days, the same rules.

Two jobs, both run by the daily workflow after the forecast is out.

Shadow forecasts, every day. Each candidate in candidates.py is
fitted on the record and asked about tomorrow, at the same reading
age the shipped forecast used. The answers are frozen in
data/shadow.json and scored when the observation lands, exactly
like the real forecast. That builds a live record for every model,
which no backtest can fake.

A walk-forward backtest, once a week. Every candidate is scored on
the same days with the same information. Anything that could ship
is refitted every day, exactly as the daily job would run it, so
the shipped model's row here is the same backtest evaluate.py
reports. The scikit-learn benchmarks are refitted weekly, because a
daily refit of a forest takes several minutes on its own. The same
run scores the shipped model at every reading age, and writes
data/leaderboard.json.

    python code/lab.py              shadow forecasts; backtest if stale
    python code/lab.py --backtest   rerun the backtest now

A challenger replaces the shipped model only by passing the rule in
PROMOTION, and only by a person changing config.SHIPPED_EXTRA in a
pull request. Nothing here changes what ships.
"""

import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import candidates
import config
import evaluate
import features

REFRESH_DAYS = 7         # rerun the backtest once it is this old
AGES = (2, 3, 4, 5, 6, 7)   # the shipped model, at every reading age
ROBUST_AGES = (2, 3, 4, 5)  # where challengers must not fall apart

# Fixed before the table was looked at, and kept in the open so
# nobody can move the bar after seeing who cleared it. Skills are
# fractions of operational persistence's error.
PROMOTION = {
    # clearly better where a forecast matters most
    "burning_gain": 0.03,
    # and no more than a point or two worse the rest of the year
    "calm_cost": 0.02,
    # and no blow-up at older readings: within 5% of the shipped
    # model's error at every age in ROBUST_AGES
    "robust_cost": 0.05,
    # and no worse on its live shadow forecasts, once enough scored
    "live_days": 20,
}


def walk(candidate, samples):
    """Walk-forward predictions for one candidate, as {day: value}.

    Training follows evaluate.published(): only rows whose readings
    were out when the target's forecast would have been issued. The
    candidate is refitted every `refit_every` days, and the days in
    between are predicted by the last fit.
    """
    ready = features.usable(samples)
    preds, block = {}, []
    fitted, fitted_on = None, None

    def flush():
        if fitted is not None and block:
            for s, v in zip(block, fitted.predict_many(block)):
                if v is not None:
                    preds[s.day] = v
        block.clear()

    for i, target in enumerate(ready):
        train = evaluate.published(ready[:i], target)
        if len(train) < evaluate.MIN_TRAIN:
            continue
        due = fitted is None or (
            (target.day - fitted_on).days >= candidate.refit_every)
        if due:
            flush()
            try:
                fitted, fitted_on = candidate.fit(train), target.day
            except ValueError:
                if fitted is None:
                    continue
        block.append(target)
    flush()
    return preds


def seasons(days):
    calm = [d for d in days if d.month not in config.BURNING_MONTHS]
    burn = [d for d in days if d.month in config.BURNING_MONTHS]
    return {"overall": list(days), "calm": calm, "burning": burn}


def skill(model_mae, ref_mae):
    if model_mae is None or not ref_mae:
        return None
    return round((ref_mae - model_mae) / ref_mae, 4)


def table(preds, truth, days):
    """Score every candidate on `days`, overall and by season."""
    out = {}
    for key, got in preds.items():
        out[key] = {}
        for name, picked in seasons(days).items():
            out[key][name] = evaluate.score(
                [(truth[d], got.get(d)) for d in picked])
    ref = out.get("persistence", {})
    for key, entry in out.items():
        entry["skill"] = {
            name: skill((entry.get(name) or {}).get("mae"),
                        (ref.get(name) or {}).get("mae"))
            for name in ("overall", "calm", "burning")}
    return out


def run_lineup(rows, lineup, age, keys=None):
    """Walk every candidate (or those in `keys`) at one age."""
    have_sklearn = candidates.sklearn_available()
    sets, preds = {}, {}
    for c in lineup:
        if keys is not None and c.key not in keys:
            continue
        if isinstance(c, candidates.Ensemble):
            continue
        if c.sklearn and not have_sklearn:
            continue
        if c.extra not in sets:
            sets[c.extra] = features.build(rows, age=age, extra=c.extra)
        preds[c.key] = walk(c, sets[c.extra])
        print(f"  age {age}: {c.key:18s} {len(preds[c.key])} days")

    members = candidates.Ensemble.members
    if (keys is None or "ensemble" in keys) and all(m in preds
                                                    for m in members):
        common = set.intersection(*(set(preds[m]) for m in members))
        preds["ensemble"] = {d: candidates.Ensemble.combine(
            [preds[m][d] for m in members]) for d in common}

    base = sets.get(()) or features.build(rows, age=age)
    truth = {s.day: s.y for s in features.usable(base)}
    days = sorted(set(truth).intersection(*(set(p) for p in preds.values())))
    return preds, truth, days


def passes_reference(entry, shipped):
    """The skill half of the rule, at the reference age only."""
    sk, ship = (entry or {}).get("skill") or {}, shipped.get("skill") or {}
    if None in (sk.get("burning"), ship.get("burning"),
                sk.get("calm"), ship.get("calm")):
        return False
    return (sk["burning"] - ship["burning"] >= PROMOTION["burning_gain"]
            and ship["calm"] - sk["calm"] <= PROMOTION["calm_cost"])


def obs_weight(rows, age, extra=()):
    """How much the shipped model leans on the station reading.

    The standardised weight on obs_recent_log, fitted on the whole
    record at one age. It should fall as the reading gets older,
    which is the reason each age has its own model.
    """
    ready = features.usable(features.build(rows, age=age, extra=extra))
    if len(ready) <= evaluate.MIN_TRAIN:
        return None
    model = evaluate.fit(ready)
    return round(dict(zip(model.names, model.coef))["obs_recent_log"], 4)


def backtest(rows=None, lineup=None):
    """The full lab run. Returns the leaderboard as a dict."""
    rows = features.load() if rows is None else rows
    lineup = lineup or candidates.lineup(config.SHIPPED_EXTRA)
    ref = config.OBS_REFERENCE_AGE

    print(f"lab: every candidate at the reference age ({ref} days)")
    preds, truth, days = run_lineup(rows, lineup, ref)
    scores = table(preds, truth, days)

    # The shipped model at every age, against persistence of the
    # same age. Kept for the robustness check below as well.
    print("lab: the shipped model at every reading age")
    by_age, ridge_at = [], {}
    for age in AGES:
        p, t, d = run_lineup(rows, lineup, age, keys={"ridge",
                                                      "persistence"})
        ridge_at[age] = (p.get("ridge", {}), t)
        s = table(p, t, d)
        ridge = s.get("ridge", {})
        if not d or not ridge.get("overall"):
            continue
        by_age.append({
            "age": age,
            "days": len(d),
            "mae": ridge["overall"]["mae"],
            "persistence_mae": s["persistence"]["overall"]["mae"],
            "skill": ridge["skill"]["overall"],
            "calm_skill": ridge["skill"]["calm"],
            "burning_skill": ridge["skill"]["burning"],
            "obs_weight": obs_weight(rows, age, config.SHIPPED_EXTRA),
        })

    # Challengers that pass at the reference age are run at the
    # other ages too. The smoke terms pass at two days and fall
    # apart at three and four: early in the 2025 season, with a
    # handful of burning days to learn from, the penalty chosen on a
    # validation tail with none in it came out near zero, and one
    # forecast for a day that measured 13 came out at 2684. A rule
    # that looked at one age would have shipped that.
    robust = {}
    shipped = scores.get("ridge", {})
    challengers = [c for c in lineup if c.shippable and c.key != "ridge"
                   and passes_reference(scores.get(c.key), shipped)]
    if challengers:
        print("lab: challengers that pass, at older readings")
    for c in challengers:
        robust[c.key] = {}
        for age in ROBUST_AGES:
            if age == ref:
                mine, theirs = preds.get(c.key, {}), preds.get("ridge", {})
            else:
                p, _, _ = run_lineup(rows, lineup, age, keys={c.key})
                mine, theirs = p.get(c.key, {}), ridge_at[age][0]
            truth_at = ridge_at[age][1]
            common = sorted(set(mine) & set(theirs) & set(truth_at))
            if not common:
                continue
            a = sum(abs(mine[d] - truth_at[d]) for d in common) / len(common)
            b = sum(abs(theirs[d] - truth_at[d]) for d in common) / len(common)
            robust[c.key][str(age)] = round(a / b, 4) if b else None

    models = []
    for c in lineup:
        if c.key not in scores:
            continue
        entry = c.describe() | scores[c.key]
        entry["shipped"] = c.key == "ridge"
        if c.key in robust:
            entry["robust"] = robust[c.key]
        models.append(entry)

    now = datetime.now(config.IST)
    board = {
        "generated_at": now.isoformat(timespec="seconds"),
        "backtest_on": now.date().isoformat(),
        "reference_age": ref,
        "window": {"first": days[0].isoformat() if days else None,
                   "last": days[-1].isoformat() if days else None},
        "days": len(days),
        "sklearn": candidates.sklearn_available(),
        "rule": PROMOTION,
        "models": models,
        "by_age": by_age,
    }
    return board


# --- shadow forecasts ---------------------------------------------

def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def shadow(rows, lineup, today, record=None):
    """Every candidate's forecast for tomorrow, as {key: value}.

    `record` is the shipped forecast, if one was issued. Its number
    is used for the ridge entry, so the leaderboard's live record
    for the shipped model is the real one and not a recomputation,
    but only when it was made from a reading of the same age as
    everyone else's. A forecast frozen earlier from an older reading,
    as on the morning a new version is merged, would not be a fair
    comparison; the ridge entry is then refitted like the others.
    """
    tomorrow = today + timedelta(days=1)
    age = features.freshest_age(rows, tomorrow)
    if age is None:
        return None, None
    have_sklearn = candidates.sklearn_available()
    out, sets = {}, {}
    for c in lineup:
        if isinstance(c, candidates.Ensemble):
            continue
        if c.sklearn and not have_sklearn:
            continue
        if c.extra not in sets:
            sets[c.extra] = features.build(rows, age=age, extra=c.extra)
        samples = sets[c.extra]
        target = next((s for s in samples if s.day == tomorrow), None)
        ready = [s for s in features.usable(samples) if s.day < tomorrow]
        if target is None or not target.complete or len(ready) < \
                evaluate.MIN_TRAIN:
            continue
        try:
            value = c.fit(ready).predict(target)
        except ValueError:
            continue
        if value is not None:
            out[c.key] = round(value, 2)
    made_at = ((record or {}).get("inputs") or {}).get("obs_age_days")
    if (record and record.get("date") == tomorrow.isoformat()
            and made_at == age):
        out["ridge"] = record["pm25"]
    members = candidates.Ensemble.members
    if all(m in out for m in members):
        out["ensemble"] = round(candidates.Ensemble.combine(
            [out[m] for m in members]), 2)
    return age, out


def freeze(book, day, issued, age, models):
    """Add tomorrow's shadow forecasts, unless the day already has some.

    Same rule as predict.py: a forecast is written once. A rerun on
    the same morning leaves the first one standing.
    """
    if day in book or not models:
        return False
    book[day] = {"date": day, "issued": issued, "age": age,
                 "models": models, "actual": None}
    return True


def attach(book, samples):
    """Fill in the observation for shadow days that have one now."""
    truth = {s.day.isoformat(): s.y for s in samples
             if s.y is not None and s.valid_target}
    filled = 0
    for day, entry in book.items():
        if entry.get("actual") is None and day in truth:
            entry["actual"] = round(truth[day], 2)
            filled += 1
    return filled


def live_scores(book, shipped="ridge"):
    """Each model's live MAE, paired with the shipped model's.

    A model is scored on the days both it and the shipped model
    answered, and the shipped model's error on those same days is
    kept beside it. A model that skipped the hard days cannot look
    better for it, and one that missed a single morning does not
    drop off the board.
    """
    scored = [e for e in book.values() if e.get("actual") is not None
              and shipped in e["models"]]
    keys = {k for e in scored for k in e["models"]}
    out = {}
    for key in sorted(keys):
        days = [e for e in scored if key in e["models"]]
        mine = [abs(e["models"][key] - e["actual"]) for e in days]
        theirs = [abs(e["models"][shipped] - e["actual"]) for e in days]
        out[key] = {"n": len(days),
                    "mae": round(sum(mine) / len(days), 2),
                    "shipped_mae": round(sum(theirs) / len(days), 2)}
    return out


def verdict(entry, shipped, live):
    """Where a challenger stands against the promotion rule."""
    if entry.get("shipped"):
        return "Shipped"
    if entry["kind"] == "baseline":
        return "Baseline"
    if not entry.get("shippable"):
        return "Benchmark: needs scikit-learn"
    sk, ship_sk = entry.get("skill") or {}, shipped.get("skill") or {}
    if None in (sk.get("burning"), ship_sk.get("burning"),
                sk.get("calm"), ship_sk.get("calm")):
        return "Not enough days to judge"
    if sk["burning"] - ship_sk["burning"] < PROMOTION["burning_gain"]:
        return "Not clearly better in burning season"
    if ship_sk["calm"] - sk["calm"] > PROMOTION["calm_cost"]:
        return "Costs too much in calm season"
    worst = max(((r, a) for a, r in (entry.get("robust") or {}).items()
                 if r is not None), default=None)
    if worst and worst[0] > 1 + PROMOTION["robust_cost"]:
        return f"Breaks down with {worst[1]}-day-old readings"
    mine = live.get(entry["key"])
    if not mine or mine["n"] < PROMOTION["live_days"]:
        have = mine["n"] if mine else 0
        return (f"Passes the backtest; {have} of "
                f"{PROMOTION['live_days']} live days so far")
    if mine["mae"] > mine["shipped_mae"]:
        return "Passes the backtest, but not live"
    return "Ready to promote"


def refresh_verdicts(board, book):
    """Re-judge every model against today's live record."""
    live = live_scores(book)
    board["live"] = live
    board["updated_at"] = datetime.now(config.IST).isoformat(
        timespec="seconds")
    shipped = next((m for m in board.get("models", [])
                    if m.get("shipped")), {})
    for entry in board.get("models", []):
        entry["verdict"] = verdict(entry, shipped, live)
    return board


def stale(board, today, lineup=None):
    """Whether the leaderboard's backtest needs running again.

    Once a week, and also as soon as a candidate joins the line-up,
    so a new challenger is on the board the next morning rather than
    up to a week later. A scikit-learn model only counts when
    scikit-learn is installed to run it.
    """
    on = (board or {}).get("backtest_on")
    if not on:
        return True
    if lineup is not None:
        have = {m["key"] for m in board.get("models", [])}
        runnable = candidates.sklearn_available()
        want = {c.key for c in lineup if runnable or not c.sklearn}
        if want - have:
            return True
    return (today - date.fromisoformat(on)).days >= REFRESH_DAYS


def main():
    today = datetime.now(config.IST).date()
    rows = features.load()
    lineup = candidates.lineup(config.SHIPPED_EXTRA)
    if not candidates.sklearn_available():
        print("scikit-learn is not installed: the forest, boosting, "
              "network and ensemble are skipped")

    # Shadow forecasts first: they are the cheap part, and the part
    # that cannot be made up later if the run dies.
    book = {e["date"]: e for e in load_json(config.SHADOW_JSON, {}).get(
        "forecasts", [])}
    predictions = load_json(config.PREDICTIONS_JSON, {})
    tomorrow = (today + timedelta(days=1)).isoformat()
    record = next((r for r in predictions.get("predictions", [])
                   if r["date"] == tomorrow), None)
    age, models = shadow(rows, lineup, today, record)
    if models and freeze(book, tomorrow, today.isoformat(), age, models):
        print(f"shadow {tomorrow} (age {age}): "
              + ", ".join(f"{k} {v:.0f}" for k, v in models.items()))
    filled = attach(book, features.build(rows))
    if filled:
        print(f"attached {filled} observation(s) to shadow forecasts")
    with open(config.SHADOW_JSON, "w") as f:
        json.dump({"forecasts": [book[d] for d in sorted(book)]}, f,
                  indent=1)

    board = load_json(config.LEADERBOARD_JSON, None)
    if "--backtest" in sys.argv or stale(board, today, lineup):
        board = backtest(rows, lineup)
    if not board:
        return 1
    refresh_verdicts(board, book)
    with open(config.LEADERBOARD_JSON, "w") as f:
        json.dump(board, f, indent=1)

    print(f"\n{'model':28s}{'MAE':>8s}{'skill':>9s}{'burning':>9s}  verdict")
    for m in board["models"]:
        o = m.get("overall") or {}
        sk = m.get("skill") or {}

        def pct(v):
            return "-" if v is None else f"{v * 100:+.1f}%"
        print(f"{m['label']:28s}{o.get('mae', 0):8.2f}"
              f"{pct(sk.get('overall')):>9s}{pct(sk.get('burning')):>9s}"
              f"  {m['verdict']}")
    print(f"\nwrote {config.SHADOW_JSON.name}, "
          f"{config.LEADERBOARD_JSON.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
