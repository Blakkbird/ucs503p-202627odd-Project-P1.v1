"""Tests for the check that decides whether a scheduled run works."""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config
import due


def at(hour, day=15):
    return datetime(2026, 11, day, hour, 0, tzinfo=config.IST)


ISSUED = {"predictions": [{"date": "2026-11-16"}]}
FAILED = {"predictions": [], "status": {
    "target": "2026-11-16", "issued": False,
    "reason": "the inputs for that day were not fetched"}}
BACKUP = "30 7 * * *"


def test_runs_started_by_hand_always_go_ahead():
    assert due.needed(ISSUED, at(9), "workflow_dispatch", "")[0]


def test_the_morning_run_always_goes_ahead():
    assert due.needed(ISSUED, at(15), "schedule", due.MORNING)[0]


def test_a_backup_stands_down_once_the_forecast_is_out():
    run, why = due.needed(ISSUED, at(16), "schedule", BACKUP)
    assert not run and "already out" in why


def test_a_backup_steps_in_after_a_failed_run():
    run, why = due.needed(FAILED, at(16), "schedule", BACKUP)
    assert run and "not fetched" in why


def test_a_backup_never_beats_the_morning_run():
    """GitHub starts the morning run hours late. A backup that fires
    on time must not issue tomorrow's forecast first, from a staler
    reading."""
    yesterday = {"predictions": [], "status": {"target": "2026-11-15"}}
    run, why = due.needed(yesterday, at(10), "schedule", BACKUP)
    assert not run and "waiting" in why


def test_in_the_evening_a_backup_stops_waiting():
    """When GitHub drops the morning run altogether."""
    yesterday = {"predictions": [], "status": {"target": "2026-11-15"}}
    assert due.needed(yesterday, at(due.EVENING_HOUR), "schedule",
                      BACKUP)[0]


def test_a_backup_pushed_past_midnight_waits_for_that_days_run():
    run, _ = due.needed(ISSUED, at(1, day=16), "schedule", BACKUP)
    assert not run


def test_the_morning_cron_matches_the_workflow():
    workflow = (Path(__file__).resolve().parents[2] / ".github" /
                "workflows" / "ingest.yml").read_text()
    assert f'cron: "{due.MORNING}"' in workflow
    first = workflow.index("cron:")
    assert workflow.index(f'cron: "{due.MORNING}"') == first
