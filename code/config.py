"""Project-wide settings. Nothing here should be duplicated elsewhere."""

import os
from datetime import timedelta, timezone
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

# India Standard Time. Every date the project writes is an IST date.
IST = timezone(timedelta(hours=5, minutes=30))

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

# The forecast for day D is issued on D-1, and it can only use
# station readings that have been published by then. How old the
# newest one is depends on the feed, and the feed has not been
# steady: in August it ran three days behind, in early October it
# came in batches, and since late October it has published each
# day by the next afternoon.
#
# This used to be one fixed lag of three days. That stopped being
# true, and the fixed rule then threw away readings the job already
# had: the forecast for 3 November was built from 30 October's
# 11.4 while 31 October (79) and 1 November (106) sat in daily.csv.
# So the lag is no longer assumed. A reading's age is counted from
# the target day (a reading from D-2 is two days old), the job
# looks for the freshest valid one on file, and the forecast is
# made by a model fitted on readings of exactly that age. Each age
# gets its own model and its own backtest, so a model is never fed
# a reading fresher or staler than the ones it learnt from.

# The issue day itself is never a complete day when the job runs,
# so the freshest reading a day-ahead forecast can have is from D-2.
OBS_MIN_AGE = 2

# Older than this and there is no forecast: the reading says too
# little about tomorrow to be worth leaning on. Seven is where the
# old rule stopped too (three days of lag plus three of lookback).
OBS_MAX_AGE = 7

# The freshness the headline backtest is run at. Two days is what
# the feed has delivered since late October; the model lab scores
# every other age as well, so a slower feed is measured, not hidden.
OBS_REFERENCE_AGE = 2

# How stale the freshest observation may get before the daily job
# treats it as a broken feed rather than a slow one. A day or two
# with no reading is ordinary; a week means nobody is writing
# ground truth any more and the training set has stopped growing.
# Kept above OBS_MAX_AGE - 1 (the same limit counted from the issue
# day), so that by the time it trips the forecast has already run
# out of readings to use.
OBS_STALENESS_LIMIT_DAYS = 7

# FIRMS reports detections for days that have already happened,
# so on the morning of D-1 the freshest complete count is D-2. The
# fire feature is lagged to match. This is not only a matter of
# availability: smoke lifted off a field upwind takes the better
# part of a day to arrive, so yesterday's fires are the ones that
# describe tomorrow's air anyway.
FIRE_LATENCY_DAYS = 1

# Paddy residue burning upwind of Patiala. Errors in this window
# are much larger, so it is scored as its own season.
BURNING_MONTHS = (10, 11)

# CPCB will not call a 24-hour average valid unless at least this
# many hourly readings went into it. Days below the line are still
# ingested and still shown, but they are not used as training
# targets and not scored: a 14-hour mean is a different quantity
# from the one the model is meant to predict, and letting it in
# adds noise to both the fit and the accuracy claim. Rows from the
# early backfill have no hour count at all and are taken on trust,
# since the API aggregated them the same way.
MIN_OBS_HOURS = 16

# --- paths 

DATA = ROOT / "data"
DAILY_CSV = DATA / "daily.csv"
PREDICTIONS_JSON = DATA / "predictions.json"
METRICS_JSON = DATA / "metrics.json"
MODEL_JSON = DATA / "model.json"
BACKTEST_JSON = DATA / "backtest.json"  # one walk-forward forecast per day
FIRES_JSON = DATA / "fires.json"  # where the most recent fires were
OUTLOOK_JSON = DATA / "outlook.json"  # CAMS and weather for days 2 and 3
LEADERBOARD_JSON = DATA / "leaderboard.json"  # the model lab's table
SHADOW_JSON = DATA / "shadow.json"  # every candidate's daily forecast
DASHBOARD_JSON = ROOT / "docs" / "dashboard" / "data.json"

# --- model

# Interaction terms the shipped model is fitted with, on top of the
# plain inputs. Empty: the plain ridge ships. Changing this is how a
# challenger is promoted, and only after it passes the rule in
# code/lab.py. The smoke terms ("burn_fire", "burn_wind_u") are the
# obvious next candidate, and the lab says why they are not here.
SHIPPED_EXTRA = ()

# The outlook: forecasts two and three days ahead, made from the
# same reading as tomorrow's. Read further from the reading, so
# less sure, and scored separately.
OUTLOOK_HORIZONS = (2, 3)

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
