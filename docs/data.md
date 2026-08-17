# Data

Everything lives in one file, `data/daily.csv`, one row per
calendar day in IST. It is committed to git, so its history is the
commit log and any correction is visible as a diff. At this size
that is worth more than a database.

## Columns

| Column | Meaning |
| --- | --- |
| `date` | The day the row describes, IST. |
| `obs_pm25` | Observed daily mean PM2.5 at Model Town, µg/m³. The target. |
| `obs_hours` | How many hourly readings that mean is built from. Blank for rows seeded by `bootstrap.py`, which used the daily endpoint. |
| `cams_pm25` | CAMS global PM2.5 forecast for this day, daily mean, µg/m³. |
| `cams_issue_date` | The day that forecast was issued. Blank means backfilled. |
| `temp_mean` | Daily mean 2 m temperature, °C. |
| `rh_mean` | Daily mean relative humidity, %. |
| `wind_speed_mean` | Daily mean 10 m wind speed, km/h. |
| `wind_dir_mean` | Daily mean 10 m wind bearing, degrees. Vector mean, not arithmetic. |
| `fire_count` | VIIRS fire detections in the upwind box that day. |
| `ingested_at` | When the row was last written, IST. |

## Sources

**Observations** come from OpenAQ v3, location 5544, sensor
`12235142`. The station exposes a second PM2.5 sensor, `15243`,
which has not reported since October 2022 but still serves its old
series on request. Both ids are pinned in `config.py` so nobody
reverses the choice by accident. The v3 aggregate endpoints ignore
parameters they do not recognise rather than rejecting them, so
every window is filtered again client-side.

**Forecast and weather** come from Open-Meteo, `cams_global`
domain for PM2.5. CAMS global publishes every 12 hours at
three-hourly resolution; the hourly series is interpolated from
that, and the daily mean is taken over the interpolated hours.

**Fires** come from NASA FIRMS, VIIRS products, over the box
`73.8, 27.5, 77.7, 32.6` — Punjab and Haryana upwind of Patiala.
The near-real-time products only keep a rolling window and answer
with an empty CSV rather than an error outside it, so the ingest
picks a product per date from the availability endpoint and
records nothing when none of them reaches back far enough.

## Two kinds of row, and why it matters

Rows arrive by two routes and they are not equivalent.

**Live rows** are written each morning by
`code/ingest/run_daily.py`. They carry a `cams_issue_date`, which
proves the forecast existed before the day it describes. These are
the rows the final evaluation rests on.

**Backfilled rows** were seeded once by `scripts/bootstrap.py`
from the CAMS archive, and their meteorology was filled in later
by `scripts/backfill_history.py`. They have no issue date, because
the archive serves a series stitched from many model runs and does
not say which run any given value came from. The lead time is
therefore unknown and probably shorter than a real day-ahead
forecast, which makes these rows mildly optimistic.

They are still used, because three months of slightly optimistic
history beats three weeks of perfect history and a model that
cannot be fitted at all. What they are not allowed to do is quietly
become the headline number. `features.py` marks each row with
`live`, the test suite refuses any row whose issue date is not
strictly before its target day, and the honest comparison is the
live-only subset once enough of it exists.

`scripts/backfill_history.py` prints which archive answered, and
that is recorded in the journal, because it changes how the
meteorology should be read.

## Holes

Gaps are left as blank cells rather than interpolated. A missing
day is information — usually the station was down — and filling it
in with a plausible number would hide that from the model and from
us. `features.py` drops any row without a complete feature vector
and reports the per-column count, so a small training set can be
traced to the column responsible instead of being blamed on the
model.

The CPCB feed also runs late. Measured on 17 August 2026, the
freshest published observation was 14 August: a three day lag.
That is not a gap that fills itself in time to be useful, and it
shapes the whole design. See [Method](method.md).
