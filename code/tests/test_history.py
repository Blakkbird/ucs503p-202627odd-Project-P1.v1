"""Tests for the history tools in scripts/.

They run once, by hand or from a manual workflow, which is exactly
why they need tests: nobody watches them closely enough to notice
a value quietly overwritten in a table of six hundred rows. Network
calls are not tested here, only what is done with the answers.
"""

import sys
from datetime import date, timedelta
from itertools import pairwise
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code"))
sys.path.insert(0, str(ROOT / "code" / "ingest"))
sys.path.insert(0, str(ROOT / "scripts"))
import backfill_history
import config
import extend_history
import run_daily


def row(day, **cells):
    out = run_daily.blank(date.fromisoformat(day))
    out.update({k: str(v) for k, v in cells.items()})
    return out


# --- extend_history ---------------------------------------------

def test_chunks_cover_the_range_without_gaps_or_overlap():
    first, last = date(2025, 2, 1), date(2026, 10, 5)
    pieces = list(extend_history.chunks(first, last, 90))
    assert pieces[0][0] == first and pieces[-1][1] == last
    for (_, end), (start, _) in pairwise(pieces):
        assert start == end + timedelta(days=1)
    assert all((end - start).days < 90 for start, end in pieces)


def test_a_single_day_range_is_one_chunk():
    day = date(2025, 10, 1)
    assert list(extend_history.chunks(day, day, 90)) == [(day, day)]


def test_cams_days_with_too_few_hours_are_dropped():
    times = [f"2025-10-01T{h:02d}:00" for h in range(24)]
    times += [f"2025-10-02T{h:02d}:00" for h in range(6)]
    values = [80.0] * 24 + [500.0] * 6
    means = extend_history.cams_means(times, values)
    assert means == {"2025-10-01": 80.0}


def test_missing_days_are_added_with_their_cams():
    rows = {"2026-05-15": row("2026-05-15", obs_pm25=30.1)}
    obs = {"2025-10-20": (142.5, 24)}
    cams = {"2025-10-20": 310.0}
    counts = extend_history.merge(rows, obs, cams, "stamp")
    added = rows["2025-10-20"]
    assert counts["added"] == 1
    assert added["obs_pm25"] == 142.5 and added["obs_hours"] == 24
    assert added["cams_pm25"] == 310.0
    assert added["cams_issue_date"] == "", "archive rows are never live"


def test_a_day_with_cams_but_no_observation_is_not_added():
    rows = {}
    extend_history.merge(rows, {}, {"2025-10-20": 310.0}, "stamp")
    assert rows == {}


def test_existing_values_are_left_alone():
    rows = {"2026-05-15": row("2026-05-15", obs_pm25=30.1, obs_hours=24,
                              cams_pm25=65.84)}
    extend_history.merge(rows, {"2026-05-15": (99.0, 24)},
                         {"2026-05-15": 999.0}, "stamp")
    assert rows["2026-05-15"]["obs_pm25"] == "30.1"
    assert rows["2026-05-15"]["cams_pm25"] == "65.84"


def test_a_blank_hour_count_is_filled_when_the_means_agree():
    rows = {"2026-05-15": row("2026-05-15", obs_pm25=30.1)}
    counts = extend_history.merge(rows, {"2026-05-15": (30.1, 22)}, {},
                                  "stamp")
    assert counts["hours_filled"] == 1
    assert rows["2026-05-15"]["obs_hours"] == 22


def test_a_blank_hour_count_is_not_filled_when_they_disagree():
    """A different mean means a different reading; its count
    says nothing about the one in the table."""
    rows = {"2026-05-15": row("2026-05-15", obs_pm25=30.1)}
    extend_history.merge(rows, {"2026-05-15": (35.0, 22)}, {}, "stamp")
    assert rows["2026-05-15"]["obs_hours"] == ""


def test_a_thin_day_is_refreshed_like_the_daily_job_does():
    rows = {"2026-10-02": row("2026-10-02", obs_pm25=41.2, obs_hours=14)}
    counts = extend_history.merge(rows, {"2026-10-02": (37.9, 24)}, {},
                                  "stamp")
    assert counts["obs_filled"] == 1
    assert rows["2026-10-02"]["obs_pm25"] == 37.9


# --- backfill_history -------------------------------------------

WX = {"temp_mean": 30.0, "rh_mean": 50.0,
      "wind_speed_mean": 6.0, "wind_dir_mean": 300.0}


def test_force_never_touches_a_live_row():
    """A live row's weather is the forecast that was really issued.
    No archive is a better source for it than that."""
    rows = {"2026-09-01": row("2026-09-01", cams_issue_date="2026-08-31",
                              temp_mean=27.0, rh_mean=80.0,
                              wind_speed_mean=5.0, wind_dir_mean=120.0)}
    backfill_history.apply(rows, {"2026-09-01": WX}, {}, force=True)
    assert rows["2026-09-01"]["temp_mean"] == "27.0"


def test_force_replaces_a_backfilled_row():
    rows = {"2026-06-20": row("2026-06-20", temp_mean=27.0, rh_mean=80.0,
                              wind_speed_mean=5.0, wind_dir_mean=120.0)}
    backfill_history.apply(rows, {"2026-06-20": WX}, {}, force=True)
    assert rows["2026-06-20"]["temp_mean"] == 30.0


def test_without_force_only_blanks_are_filled():
    rows = {"2026-06-20": row("2026-06-20", temp_mean=27.0)}
    backfill_history.apply(rows, {"2026-06-20": WX}, {})
    assert rows["2026-06-20"]["temp_mean"] == "27.0"
    assert rows["2026-06-20"]["rh_mean"] == 50.0


def test_a_live_row_with_a_blank_still_gets_it_filled():
    rows = {"2026-09-01": row("2026-09-01", cams_issue_date="2026-08-31")}
    backfill_history.apply(rows, {"2026-09-01": WX}, {}, force=True)
    assert rows["2026-09-01"]["temp_mean"] == 30.0


def test_fire_counts_are_never_replaced():
    rows = {"2025-10-20": row("2025-10-20", fire_count=812)}
    backfill_history.apply(rows, {}, {"2025-10-20": 5}, force=True)
    assert rows["2025-10-20"]["fire_count"] == "812"


def test_a_day_missing_one_variable_is_left_out_whole():
    """No row should get temperature from one archive and wind from
    another."""
    times = [f"2025-10-01T{h:02d}:00" for h in range(24)]
    hourly = {name: [10.0] * 24 for name in backfill_history.VARIABLES}
    hourly["wind_direction_10m"] = [None] * 24
    got = backfill_history.day_rows(times, hourly, "", [date(2025, 10, 1)])
    assert got == {}


def test_a_complete_day_comes_back_with_all_four_columns():
    times = [f"2025-10-01T{h:02d}:00" for h in range(24)]
    hourly = {name: [10.0] * 24 for name in backfill_history.VARIABLES}
    got = backfill_history.day_rows(times, hourly, "", [date(2025, 10, 1)])
    assert set(got["2025-10-01"]) == set(backfill_history.WEATHER_COLUMNS)


# --- FIRMS ------------------------------------------------------

def test_firms_products_are_tried_in_a_fixed_order():
    names = ["VIIRS_NOAA21_NRT", "VIIRS_NOAA20_NRT", "VIIRS_SNPP_NRT",
             "VIIRS_NOAA20_SP", "VIIRS_SNPP_SP"]
    ordered = sorted(names, key=run_daily.source_rank)
    assert ordered == ["VIIRS_SNPP_SP", "VIIRS_SNPP_NRT", "VIIRS_NOAA20_SP",
                       "VIIRS_NOAA20_NRT", "VIIRS_NOAA21_NRT"]


def test_the_extension_starts_inside_the_sensor_record():
    """Before February 2025 this sensor has nothing to give."""
    assert extend_history.SENSOR_START >= date(2025, 1, 1)
    assert config.OPENAQ_PM25_SENSOR_ID == 12235142
