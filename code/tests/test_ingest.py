"""Tests for the daily ingest.

Only the parts that do not touch the network. The one worth having
is the staleness tripwire: the failure it catches is invisible by
construction, because every symptom of it looks like success.
"""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ingest"))
import config
import run_daily


def table(last_obs_day, today, n=40):
    """A table ending at `today` whose observations stop earlier.

    Every row gets a forecast, so the only thing that varies is
    how far back the freshest observation sits.
    """
    rows = {}
    for i in range(n):
        day = today - timedelta(days=n - 1 - i)
        rows[day.isoformat()] = {
            "date": day.isoformat(),
            "obs_pm25": "42.0" if day <= last_obs_day else "",
            "obs_hours": "24" if day <= last_obs_day else "",
            "cams_pm25": "50.0",
        }
    return rows


def test_staleness_counts_from_the_freshest_observation():
    today = date(2026, 8, 30)
    rows = table(date(2026, 8, 14), today)
    assert run_daily.obs_staleness(rows, today) == 16


def test_a_current_feed_is_not_stale():
    today = date(2026, 8, 30)
    rows = table(today - timedelta(days=config.OBS_LATENCY_DAYS), today)
    assert (run_daily.obs_staleness(rows, today)
            <= config.OBS_STALENESS_LIMIT_DAYS)


def test_normal_publication_delay_does_not_trip_the_limit():
    """The lag the feed has on a good day must stay under the
    limit, or the job would cry wolf every morning."""
    assert config.OBS_LATENCY_DAYS < config.OBS_STALENESS_LIMIT_DAYS


def test_empty_record_reports_none_rather_than_zero():
    """Nothing at all is not the same as fresh, and returning 0
    here would read as the healthiest possible feed."""
    today = date(2026, 8, 30)
    rows = table(date(2020, 1, 1), today)
    assert run_daily.obs_staleness(rows, today) is None


def test_backfill_window_outlasts_the_staleness_limit():
    """The window has to be wide enough to still reach the days
    that went missing while the feed was down, otherwise the job
    reports the problem and then cannot fix it."""
    assert run_daily.BACKFILL_DAYS > config.OBS_STALENESS_LIMIT_DAYS
