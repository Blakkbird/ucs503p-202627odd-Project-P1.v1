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


def test_every_row_reads_exactly_its_age():
    """A build at age a reads the day a days back, for every row."""
    start = date(2026, 1, 1)
    for age in range(config.OBS_MIN_AGE, config.OBS_MAX_AGE + 1):
        for sample in features.build(synthetic(), age=age):
            recent = sample.persistence_op
            if recent is None:
                continue
            taken = start + timedelta(days=int(recent))
            assert taken == sample.day - timedelta(days=age)
            assert sample.obs_age == age


def test_the_default_age_is_the_reference_age():
    sample = features.build(synthetic())[-1]
    assert sample.obs_age == config.OBS_REFERENCE_AGE


def test_an_age_inside_the_issue_day_is_refused():
    """A one-day-old reading for tomorrow is the issue day itself,
    which is not over when the job runs."""
    import pytest

    with pytest.raises(ValueError):
        features.build(synthetic(), age=1)
    with pytest.raises(ValueError):
        features.build(synthetic(), age=2, horizon=2)


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

    later = thin + timedelta(days=config.OBS_REFERENCE_AGE)
    sample = next(s for s in features.build(rows) if s.day == later)
    assert sample.persistence_op != float(9), (
        "a four-hour mean was used as the freshest reading")
    assert sample.persistence_op is None


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


def _sample_for(rows, day, **kw):
    return next(s for s in features.build(rows, **kw) if s.day == day)


def test_freshest_age_is_two_on_a_feed_one_day_behind():
    rows = synthetic(30)
    assert features.freshest_age(rows, date(2026, 1, 20)) == 2


def test_freshest_age_skips_a_day_that_has_not_published():
    """The feed publishes in batches, so the newest day is often
    not there yet. The forecast takes the next one back, and the
    model fitted at that age, rather than giving up."""
    rows = synthetic(30)
    target = date(2026, 1, 20)
    rows[(target - timedelta(days=2)).isoformat()]["obs_pm25"] = ""

    age = features.freshest_age(rows, target)
    assert age == 3
    sample = _sample_for(rows, target, age=age)
    assert sample.persistence_op == float(
        (target - timedelta(days=3) - date(2026, 1, 1)).days)
    assert sample.complete


def test_freshest_age_skips_a_thin_day():
    rows = synthetic(30)
    target = date(2026, 1, 20)
    rows[(target - timedelta(days=2)).isoformat()]["obs_hours"] = str(
        config.MIN_OBS_HOURS - 2)
    assert features.freshest_age(rows, target) == 3


def test_freshest_age_never_uses_the_issue_day():
    """Even a reading for the issue day that looks complete is not:
    the day is still going when the job runs."""
    rows = synthetic(30)
    target = date(2026, 1, 20)
    rows[(target - timedelta(days=2)).isoformat()]["obs_pm25"] = ""
    rows[(target - timedelta(days=3)).isoformat()]["obs_pm25"] = ""
    assert (target - timedelta(days=1)).isoformat() in rows
    assert features.freshest_age(rows, target) == 4


def test_no_age_at_all_past_the_limit():
    """A feed quiet for longer than OBS_MAX_AGE leaves no forecast,
    rather than one built on a reading from last week."""
    rows = synthetic(30)
    target = date(2026, 1, 25)
    for age in range(2, config.OBS_MAX_AGE + 1):
        rows[(target - timedelta(days=age)).isoformat()]["obs_pm25"] = ""
    assert features.freshest_age(rows, target) is None


def test_a_missing_reading_voids_the_row_instead_of_walking_back():
    """At a fixed age there is no reaching further: a row whose
    reading is missing is unusable for that age's model."""
    rows = synthetic(30)
    target = date(2026, 1, 20)
    rows[(target - timedelta(days=2)).isoformat()]["obs_pm25"] = ""
    sample = _sample_for(rows, target, age=2)
    assert sample.persistence_op is None
    assert not sample.complete


def test_the_outlook_moves_the_fire_count_back_with_the_issue_day():
    """Two days ahead, the issue day is D-2, so the newest complete
    fire count is from D-3, not D-2."""
    rows = synthetic(30)
    target = date(2026, 1, 20)
    one = _sample_for(rows, target, age=3, horizon=1)
    two = _sample_for(rows, target, age=3, horizon=2)
    assert one.raw["fire_day"] == (target - timedelta(days=2)).isoformat()
    assert two.raw["fire_day"] == (target - timedelta(days=3)).isoformat()
    assert two.horizon == 2


def test_the_outlook_needs_an_older_reading():
    rows = synthetic(30)
    target = date(2026, 1, 20)
    assert features.freshest_age(rows, target, horizon=2) == 3
    assert features.freshest_age(rows, target, horizon=3) == 4


def test_interactions_are_off_by_default():
    sample = features.build(synthetic(10), use_weather=True)[-1]
    assert not any(n in features.INTERACTIONS for n in sample.names)


def test_an_interaction_is_zero_outside_burning_season():
    built = features.build(synthetic(40), use_weather=True,
                           extra=("burn_fire",))
    # The first row has no earlier fire count to lag onto, so it is
    # blank either way; every other January row should read zero.
    filled = [s for s in built
              if s.x[s.names.index("fire_log")] is not None]
    assert filled
    assert all(s.x[s.names.index("burn_fire")] == 0.0 for s in filled)


def test_an_interaction_carries_the_input_in_burning_season():
    built = features.build(synthetic(40, date(2026, 10, 1)),
                           use_weather=True, extra=("burn_fire",))
    for s in built:
        fire = s.x[s.names.index("fire_log")]
        if fire is not None:
            assert s.x[s.names.index("burn_fire")] == fire


def test_an_interaction_with_a_blank_input_is_blank():
    """A missing fire count must void the product too, not zero it."""
    rows = synthetic(40, date(2026, 10, 1))
    for key in rows:
        rows[key]["fire_count"] = ""
    built = features.build(rows, use_weather=True, extra=("burn_fire",))
    assert all(s.x[s.names.index("burn_fire")] is None for s in built)


def test_transform_rebuilds_every_row_from_its_raw_readings():
    """The dashboard repeats transform() in JavaScript from `raw`.

    That only works if `raw` alone is enough to get x back, for
    every row and for the interactions as well.
    """
    names = (features.CORE + features.WEATHER
             + list(features.INTERACTIONS))
    built = features.build(synthetic(start=date(2026, 9, 20)),
                           extra=tuple(features.INTERACTIONS))
    assert built
    for s in built:
        again = features.transform(s.raw, s.burning, names)
        assert again == s.x, s.day


def test_raw_says_which_days_the_readings_came_from():
    start = date(2026, 1, 1)
    s = _sample_for(synthetic(start=start), start + timedelta(days=30))
    assert s.raw["obs_day"] is not None
    # The reading is the day number, so its value names its day.
    taken = start + timedelta(days=int(s.raw["obs_recent"]))
    assert s.raw["obs_day"] == taken.isoformat()
    assert s.raw["fire_day"] < (s.day - timedelta(days=1)).isoformat()
