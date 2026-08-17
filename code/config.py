"""Project-wide settings. Nothing here should be duplicated elsewhere."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# load .env if present; a set-but-empty shell var must not shadow it (avoid big traceback error too)
_env = ROOT / ".env"
if _env.exists():
    for _line in _env.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            if not os.environ.get(_k.strip()):
                os.environ[_k.strip()] = _v.strip()

# --- station 

CITY = "Patiala"
STATION_NAME = "Model Town, Patiala - PPCB"
LAT = 30.3398
LON = 76.3869

# Two pm2.5 sensors exist for this station. 15243 stopped
# reporting in Oct 2022 but still serves its old series; 12235142
# is the live one. Resolved by scripts/check_sensor.py.
OPENAQ_LOCATION_ID = 5544
OPENAQ_PM25_SENSOR_ID = 12235142
OPENAQ_PM25_SENSOR_RETIRED = 15243

# upwind source region for residue smoke: west,south,east,north
FIRMS_BBOX = "73.8,27.5,77.7,32.6"

# --- target 

TARGET = "pm25"
TARGET_UNITS = "ug/m3"
HORIZON_DAYS = 1

# --- timing 

# The forecast for day D is issued on the morning of D-1. At that
# moment the CPCB feed has not caught up: measured on 2026-08-17,
# the freshest published observation was 2026-08-14. So anything
# the model reads about the past must stop three days short of the
# issue date. Persistence gets scored both ways, see evaluate.py.
OBS_LATENCY_DAYS = 3

# Paddy residue burning upwind of Patiala. Errors in this window
# are much larger, so it is scored as its own season.
BURNING_MONTHS = (10, 11)

# --- paths 

DATA = ROOT / "data"
DAILY_CSV = DATA / "daily.csv"
PREDICTIONS_JSON = DATA / "predictions.json"
METRICS_JSON = DATA / "metrics.json"
MODEL_JSON = DATA / "model.json"

# --- credentials 

OPENAQ_KEY = os.environ.get("OPENAQ_KEY", "")
FIRMS_MAP_KEY = os.environ.get("FIRMS_MAP_KEY", "")

# --- schema 

COLUMNS = [
    "date",
    "obs_pm25", # observed daily mean, the target
    "obs_hours", # hours behind obs_pm25
    "cams_pm25", # forecast for this date
    "cams_issue_date", # day that forecast was issued
    "temp_mean",
    "rh_mean",
    "wind_speed_mean",
    "wind_dir_mean",
    "fire_count",
    "ingested_at",
]
