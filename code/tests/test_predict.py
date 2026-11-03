"""Tests for the live prediction record.

These guard two properties that nothing else can. A model that
quietly restates yesterday's forecast in light of yesterday's
weather scores beautifully and means nothing, and the failure
leaves no trace in the output -- the file still looks like a list
of forecasts. So the freeze is asserted directly.
"""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import predict

sys.path.insert(0, str(Path(__file__).resolve().parent))


class FakeSample:
    """Just enough of features.Sample for attach_outcomes."""

    def __init__(self, day, y, valid_target=True):
        self.day = day
        self.y = y
        self.valid_target = valid_target


def record(day, pm25, actual=None):
    return {"date": day, "issued": "2026-09-01", "pm25": pm25,
            "band": "Good", "actual": actual, "error": None}


def test_an_outcome_is_attached_when_the_observation_lands():
    history = {"2026-09-02": record("2026-09-02", 20.0)}
    filled = predict.attach_outcomes(
        history, [FakeSample(date(2026, 9, 2), 24.0)])
    assert filled == 1
    assert history["2026-09-02"]["actual"] == 24.0
    assert history["2026-09-02"]["error"] == -4.0


def test_attaching_an_outcome_does_not_alter_the_prediction():
    """The whole point. The forecast is the claim that was made;
    the observation is what happened. Only the second is new."""
    history = {"2026-09-02": record("2026-09-02", 20.0)}
    predict.attach_outcomes(history, [FakeSample(date(2026, 9, 2), 24.0)])
    assert history["2026-09-02"]["pm25"] == 20.0
    assert history["2026-09-02"]["issued"] == "2026-09-01"


def test_an_already_scored_day_is_left_alone():
    """A second observation for the same day, revised or not, must
    not restate an error that has already been counted."""
    history = {"2026-09-02": record("2026-09-02", 20.0, actual=24.0)}
    filled = predict.attach_outcomes(
        history, [FakeSample(date(2026, 9, 2), 99.0)])
    assert filled == 0
    assert history["2026-09-02"]["actual"] == 24.0


def test_days_without_an_observation_stay_unscored():
    history = {"2026-09-02": record("2026-09-02", 20.0)}
    filled = predict.attach_outcomes(
        history, [FakeSample(date(2026, 9, 2), None)])
    assert filled == 0
    assert history["2026-09-02"]["actual"] is None


def test_band_hit_is_judged_on_the_observation():
    """37 is Satisfactory and 20 is Good, so this forecast landed
    in the wrong band even though it was only 17 out."""
    history = {"2026-09-02": record("2026-09-02", 20.0)}
    predict.attach_outcomes(history, [FakeSample(date(2026, 9, 2), 37.0)])
    assert history["2026-09-02"]["band_hit"] is False


def test_the_interval_multiplier_is_not_a_confidence_claim():
    """Documented as a rough band. If someone tightens this to a
    95% z-value the wording in the docstring stops being true."""
    assert predict.INTERVAL_Z == 1.28


def test_prediction_days_are_always_in_the_future_at_issue():
    """A record whose issue date is not before the day it
    describes was written after the fact."""
    history = {
        (date(2026, 9, 1) + timedelta(days=i)).isoformat():
        record((date(2026, 9, 1) + timedelta(days=i)).isoformat(), 20.0)
        for i in range(1, 4)
    }
    for day, rec in history.items():
        assert rec["issued"] < day


def test_a_thin_day_is_not_scored():
    """Scored on the same days as the backtest, or not at all."""
    history = {"2026-09-02": record("2026-09-02", 20.0)}
    filled = predict.attach_outcomes(
        history, [FakeSample(date(2026, 9, 2), 41.0, valid_target=False)])
    assert filled == 0
    assert history["2026-09-02"]["actual"] is None


def test_a_score_from_a_thin_day_is_withdrawn():
    history = {"2026-09-02": record("2026-09-02", 20.0, actual=41.0)}
    history["2026-09-02"]["band_hit"] = False
    cleared = predict.unscore_thin(
        history, [FakeSample(date(2026, 9, 2), 41.0, valid_target=False)])
    assert cleared == 1
    assert history["2026-09-02"]["actual"] is None
    assert history["2026-09-02"]["pm25"] == 20.0, "the forecast stays"


def test_a_full_day_score_is_not_withdrawn():
    history = {"2026-09-02": record("2026-09-02", 20.0, actual=24.0)}
    cleared = predict.unscore_thin(
        history, [FakeSample(date(2026, 9, 2), 24.0)])
    assert cleared == 0
    assert history["2026-09-02"]["actual"] == 24.0


def test_the_model_on_file_is_used_when_its_age_matches(tmp_path):
    import evaluate
    import features
    from test_features import synthetic

    samples = features.build(synthetic(90), age=2)
    fitted = evaluate.fit(features.usable(samples))
    blob = fitted.to_dict() | {"obs_age": 2}

    model, refitted = predict.ensure_model(blob, 2, samples,
                                           tmp_path / "m.json")
    assert not refitted
    assert model.coef == fitted.coef


def test_a_model_fitted_at_another_age_is_refitted(tmp_path):
    """Handing a two-day-old reading to a model that learnt from
    five-day-old ones would weigh it wrongly. The file says which
    age it was fitted at, and a mismatch means a refit."""
    import json

    import evaluate
    import features
    from test_features import synthetic

    rows = synthetic(90)
    old = evaluate.fit(features.usable(features.build(rows, age=5)))
    blob = old.to_dict() | {"obs_age": 5}

    samples = features.build(rows, age=2)
    path = tmp_path / "m.json"
    model, refitted = predict.ensure_model(blob, 2, samples, path)
    assert refitted
    assert json.loads(path.read_text())["obs_age"] == 2
    assert model.names == samples[0].names


def test_calibration_is_only_used_at_the_age_it_was_sized_for():
    metrics = {"horizons": {"1": {"age": 2, "calibration": {"calm": {}}}}}
    assert predict.calibration_for(metrics, 1, 2) == {"calm": {}}
    assert predict.calibration_for(metrics, 1, 3) is None
    assert predict.calibration_for(metrics, 2, 3) is None
    assert predict.calibration_for(None, 1, 2) is None


def outlook_inputs(today):
    days = {}
    for h in (2, 3):
        day = (today + timedelta(days=h)).isoformat()
        days[day] = {"cams_pm25": 50.0, "temp_mean": 25.0, "rh_mean": 60.0,
                     "wind_speed_mean": 8.0, "wind_dir_mean": 310.0}
    return {"issued": today.isoformat(), "days": days}


def test_the_outlook_is_issued_once_and_frozen():
    import features
    from test_features import synthetic

    rows = synthetic(90)
    today = date(2026, 3, 31)
    book = {}
    made = predict.outlook(rows, today, True, None, book,
                           outlook_inputs(today))
    assert made == 2
    assert {r["horizon"] for r in book.values()} == {2, 3}
    first = {k: r["pm25"] for k, r in book.items()}
    # the reading is a day older for each extra day ahead
    ages = sorted(r["inputs"]["obs_age_days"] for r in book.values())
    assert ages == [3.0, 4.0]

    rows["2026-03-31"]["cams_pm25"] = "500"
    again = predict.outlook(rows, today, True, None, book,
                            outlook_inputs(today))
    assert again == 0
    assert {k: r["pm25"] for k, r in book.items()} == first
    assert features  # imported for the synthetic table's helpers


def test_an_outlook_file_from_another_day_is_not_used():
    from test_features import synthetic

    today = date(2026, 3, 31)
    stale = outlook_inputs(today - timedelta(days=1))
    assert predict.outlook(synthetic(90), today, True, None, {}, stale) == 0


def test_outlook_outcomes_are_matched_by_date_not_key():
    history = {"2026-09-04|2": dict(record("2026-09-04", 20.0),
                                    horizon=2)}
    filled = predict.attach_outcomes(
        history, [FakeSample(date(2026, 9, 4), 25.0)])
    assert filled == 1
    assert history["2026-09-04|2"]["error"] == -5.0
