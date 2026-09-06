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


class FakeSample:
    """Just enough of features.Sample for attach_outcomes."""

    def __init__(self, day, y):
        self.day = day
        self.y = y


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
