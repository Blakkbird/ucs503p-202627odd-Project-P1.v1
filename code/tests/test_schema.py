"""Schema and config invariants. Cheap by design: no network,
so a failure here always means a real change."""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config


def test_columns_unique():
    assert len(config.COLUMNS) == len(set(config.COLUMNS))


def test_date_is_first_column():
    assert config.COLUMNS[0] == "date"


def test_station_is_configured():
    assert config.LAT and config.LON
    assert config.STATION_NAME


def test_no_hardcoded_secrets():
    """No API key may be committed in source."""
    text = Path(config.__file__).read_text()
    for name in ("OPENAQ_KEY", "DATA_GOV_KEY", "FIRMS_MAP_KEY"):
        for line in text.splitlines():
            if line.strip().startswith(f"{name} ="):
                assert "os.environ" in line, \
                    f"{name} must come from the environment"


def test_daily_csv_matches_schema():
    """Header must match the schema in config."""
    if not config.DAILY_CSV.exists():
        return
    with open(config.DAILY_CSV, newline="") as f:
        header = next(csv.reader(f))
    assert header == config.COLUMNS


def test_daily_csv_dates_unique():
    if not config.DAILY_CSV.exists():
        return
    with open(config.DAILY_CSV, newline="") as f:
        dates = [r["date"] for r in csv.DictReader(f)]
    assert len(dates) == len(set(dates))


def test_no_leakage_in_training_rows():
    """Leakage guard: a training row must have been forecast
    before the day it describes."""
    if not config.DAILY_CSV.exists():
        return
    with open(config.DAILY_CSV, newline="") as f:
        for row in csv.DictReader(f):
            issued = row.get("cams_issue_date", "")
            if issued:
                assert issued < row["date"], (
                    f"row {row['date']} was forecast on {issued}, "
                    "which is not before the day it describes")
