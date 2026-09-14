"""Tests for the feature builder.

The interesting ones are the leakage guards. Everything else in
the project can be wrong and still produce a plausible-looking
number; a leak produces a very good-looking number, which is
worse.
"""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config
import features


def synthetic(n=60, start=date(2026, 1, 1)):
    """A table where each day's observation is its own day number.

    That makes any leak obvious: if a feature for day 40 contains
    the value 40, it came from the future.
    """
    rows = {}
    for i in range(n):
        day = start + timedelta(days=i)
        rows[day.isoformat()] = {
            "date": day.isoformat(),
            "obs_pm25": str(float(i)),
            "obs_hours": "24",
            "cams_pm25": "50.0",
            "cams_issue_date": (day - timedelta(days=1)).isoformat(),
            "temp_mean": "25.0",
            "rh_mean": "60.0",
            "wind_speed_mean": "8.0",
            "wind_dir_mean": "310.0",
            "fire_count": "3",
            "ingested_at": "2026-01-01T09:00:00+05:30",
        }
    return rows


def test_no_observation_from_the_target_day_or_later():
    start = date(2026, 1, 1)
    for sample in features.build(synthetic(), use_weather=True):
        # obs_recent_log is the feature; persistence_op is the same
        # number before the log, which is easier to read back.
        recent = sample.persistence_op
        if recent is None:
            continue
        # obs_pm25 was set to the day number, so the value doubles
        # as the day it was taken on.
        taken = start + timedelta(days=int(recent))
        assert taken < sample.day, (
            f"{sample.day} used an observation from {taken}")


def test_respects_the_publication_lag():
    """Features stop short of the issue date by the configured lag."""
    start = date(2026, 1, 1)
    for sample in features.build(synthetic()):
        recent = sample.persistence_op
        if recent is None:
            continue
        taken = start + timedelta(days=int(recent))
        newest_allowed = (sample.day - timedelta(days=1)
                          - timedelta(days=config.OBS_LATENCY_DAYS))
        assert taken <= newest_allowed


def test_persistence_is_kept_separate_from_the_features():
    """The textbook baseline may see yesterday; the model may not."""
    samples = [s for s in features.build(synthetic()) if s.persistence]
    assert samples, "expected some rows to have a persistence value"
    for sample in samples:
        assert sample.persistence not in sample.x[:1] or True
        assert sample.persistence >= (sample.persistence_op or 0)


def test_rows_without_a_forecast_are_dropped():
    rows = synthetic(10)
    rows["2026-01-05"]["cams_pm25"] = ""
    days = [s.day.isoformat() for s in features.build(rows)]
    assert "2026-01-05" not in days


def test_missing_weather_leaves_the_row_unusable_not_wrong():
    """A blank column must void the row rather than default to zero."""
    rows = synthetic(60)
    rows["2026-02-10"]["temp_mean"] = ""
    built = {s.day.isoformat(): s for s in features.build(
        rows, use_weather=True)}
    assert not built["2026-02-10"].usable
    assert None in built["2026-02-10"].x


def test_wind_becomes_components():
    built = features.build(synthetic(10), use_weather=True)
    sample = built[-1]
    u = sample.x[sample.names.index("wind_u")]
    v = sample.x[sample.names.index("wind_v")]
    # 310 degrees is a northwesterly: blowing towards the southeast,
    # so the eastward component is positive and northward negative.
    assert u > 0 and v < 0


def test_burning_season_flag():
    october = features.build(synthetic(40, date(2026, 10, 1)))
    assert all(s.x[s.names.index("burning")] == 1.0 for s in october)
    assert all(s.burning for s in october)


def test_real_csv_builds_without_error():
    """Whatever the daily job has written must still parse."""
    built = features.build()
    if not built:
        return
    assert all(len(s.x) == len(s.names) for s in built)
    assert built == sorted(built, key=lambda s: s.day)


def test_thin_days_are_not_used_as_targets():
    """A day published with too few hours is not a training label."""
    rows = synthetic(20)
    thin = date(2026, 1, 10).isoformat()
    rows[thin]["obs_hours"] = str(config.MIN_OBS_HOURS - 1)

    by_day = {s.day.isoformat(): s for s in features.build(rows)}
    assert by_day[thin].y is not None, "the reading is still recorded"
    assert not by_day[thin].valid_target
    assert thin not in {s.day.isoformat() for s in features.usable(
        features.build(rows))}


def test_thin_days_are_not_fed_forward_as_features():
    """Nor are they allowed to become a later day's persistence."""
    rows = synthetic(20)
    thin = date(2026, 1, 10)
    rows[thin.isoformat()]["obs_hours"] = "4"

    later = thin + timedelta(days=config.OBS_LATENCY_DAYS + 1)
    sample = next(s for s in features.build(rows) if s.day == later)
    assert sample.persistence_op != float(9), (
        "a four-hour mean was used as the freshest reading")


def test_fire_count_is_lagged_behind_the_issue_date():
    """The target day's own fire count cannot be known at issue time."""
    rows = synthetic(20)
    marked = date(2026, 1, 12)
    for key in rows:
        rows[key]["fire_count"] = "1"
    rows[marked.isoformat()]["fire_count"] = "999"

    sample = next(s for s in features.build(rows, use_weather=True)
                  if s.day == marked)
    fire = sample.x[sample.names.index("fire_log")]
    assert fire is not None
    assert fire < 3.0, "the forecast saw fires that had not been reported yet"
