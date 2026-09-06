"""Tomorrow's forecast, written to data/predictions.json.

Until this file existed the project could measure a model and
could not use one. evaluate.py fitted, scored and saved to
data/model.json every time it ran, and then nothing applied that
model to the day in front of it. A forecasting system that never
issues a forecast is a backtest with ambitions.

Two rules hold the file honest.

A prediction is written once. If data/predictions.json already
carries a record for a target date, this leaves it exactly as it
is, even when the model has since been refitted and would now say
something different. Rewriting yesterday's forecast after
yesterday happened is how a system comes to look far better than
it is, and the numbers on the site are only worth reading if the
thing being scored is what was actually claimed at the time.

Outcomes are attached afterwards. When the observation for a
predicted day finally publishes -- three days late, sometimes more
-- it is filled in beside the frozen prediction along with the
error. That is the record the accuracy claims come from.
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config
import evaluate
import features
from model import Ridge

IST = timezone(timedelta(hours=5, minutes=30))

# An interval this wide would hold roughly four out of five days
# if the errors were normal and the backtest RMSE still described
# them. Both are approximations, so it is published as a rough
# band and named one, not as a confidence interval.
INTERVAL_Z = 1.28


def load_history():
    """Existing predictions, keyed by the day they describe."""
    if not config.PREDICTIONS_JSON.exists():
        return {}
    try:
        with open(config.PREDICTIONS_JSON) as f:
            blob = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        # Better to stop than to quietly start a fresh file and
        # lose every prediction ever made.
        raise SystemExit(f"cannot read {config.PREDICTIONS_JSON}: {e}")
    return {r["date"]: r for r in blob.get("predictions", [])}


def spread():
    """Backtest RMSE, for sizing the interval. None if unmeasured."""
    if not config.METRICS_JSON.exists():
        return None
    try:
        with open(config.METRICS_JSON) as f:
            blob = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
    return ((blob.get("overall") or {}).get("model") or {}).get("rmse")


def attach_outcomes(history, samples):
    """Fill in the truth for past predictions, once it publishes.

    The prediction itself is never touched here -- only `actual`
    and `error`, which did not exist when it was made.
    """
    truth = {s.day.isoformat(): s.y for s in samples if s.y is not None}
    filled = 0
    for day, record in history.items():
        if record.get("actual") is not None:
            continue
        actual = truth.get(day)
        if actual is None:
            continue
        record["actual"] = round(actual, 2)
        record["error"] = round(record["pm25"] - actual, 2)
        record["band_hit"] = evaluate.band(actual) == record["band"]
        filled += 1
    return filled


def describe(sample, model, rmse, today):
    """One prediction record, with enough context to explain it."""
    point = model.predict_one(sample.x)
    record = {
        "date": sample.day.isoformat(),
        "issued": today.isoformat(),
        "pm25": round(point, 2),
        "band": evaluate.band(point),
        "actual": None,
        "error": None,
    }
    if rmse:
        record["interval"] = [round(max(point - INTERVAL_Z * rmse, 0.0), 2),
                              round(point + INTERVAL_Z * rmse, 2)]

    # What the correction was applied to, and what it would have
    # been worth doing nothing. Kept per row so a bad day can be
    # read back later without rebuilding the whole dataset.
    named = dict(zip(sample.names, sample.x))
    record["inputs"] = {
        "cams_log": round(named.get("cams_log", 0.0), 4),
        "obs_age_days": named.get("obs_age"),
        "persistence_operational": (
            None if sample.persistence_op is None
            else round(sample.persistence_op, 2)),
        "forecast_provenance_live": sample.live,
    }
    return record


def main():
    weather = "--weather" in sys.argv
    today = datetime.now(IST).date()
    tomorrow = today + timedelta(days=1)

    if not config.MODEL_JSON.exists():
        print(f"no model at {config.MODEL_JSON}; run evaluate.py first")
        return 1
    model = Ridge.load(config.MODEL_JSON)

    samples = features.build(use_weather=weather)
    history = load_history()

    filled = attach_outcomes(history, samples)
    if filled:
        print(f"attached {filled} observed outcome(s) to past forecasts")

    target = next((s for s in samples if s.day == tomorrow), None)
    if target is None:
        print(f"no row for {tomorrow}; the ingest has not run today")
    elif any(v is None for v in target.x):
        missing = [n for n, v in zip(target.names, target.x) if v is None]
        print(f"{tomorrow}: incomplete features, missing {missing}")
    elif tomorrow.isoformat() in history:
        # Not an error. The job runs again, the answer stands.
        print(f"{tomorrow}: already forecast on "
              f"{history[tomorrow.isoformat()]['issued']}, left alone")
    else:
        record = describe(target, model, spread(), today)
        history[record["date"]] = record
        print(f"{record['date']}: {record['pm25']} ug/m3 "
              f"({record['band']}), issued {record['issued']}")

    out = {
        "generated_at": datetime.now(IST).isoformat(timespec="seconds"),
        "model": {
            "alpha": model.alpha,
            "features": model.names,
            "fitted_rows": len(features.usable(samples)),
        },
        "predictions": [history[d] for d in sorted(history)],
    }
    config.DATA.mkdir(exist_ok=True)
    with open(config.PREDICTIONS_JSON, "w") as f:
        json.dump(out, f, indent=2)

    scored = [r for r in out["predictions"] if r.get("actual") is not None]
    if scored:
        mae = sum(abs(r["error"]) for r in scored) / len(scored)
        hits = sum(1 for r in scored if r.get("band_hit"))
        print(f"live record: {len(scored)} scored, MAE {mae:.2f}, "
              f"band correct {hits}/{len(scored)}")
    print(f"wrote {config.PREDICTIONS_JSON} "
          f"({len(out['predictions'])} forecast(s) on record)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
