![Tiet Logo](assets/tiet-logo.svg){ .tiet-logo }

**UCS503: Software Engineering (Project)**  
**TIET Patiala**

# Pawan: Next-Day Air Quality Forecasting for Patiala

[Open the live dashboard](dashboard/index.html){ .md-button .md-button--primary }
[Tomorrow's forecast, plain](forecast.md){ .md-button }

**Author(s)**:

`(GS)` Gurkirpa Singh `<gsarao_be24 -at- thapar -dot- edu>`  
`(KB)` Ketubh Bansal `(1024170399)`  
`(AK)` Aayush Kandhol `(1024170379)`

**Instructor**: Dr. Paramveer Kaur

## What this is

A global atmospheric model called CAMS publishes a PM2.5 forecast
for every point on Earth, Patiala included. At the CPCB station in
Model Town it is badly wrong, and wrong by a different amount in
every season: it reads close to four times the observed value in
the monsoon and a little over one times in November. On a 0.4
degree grid, roughly 45 km per cell, a single number covers
Patiala and everything around it. What it cannot know is what this
particular station reads.

Pawan learns that difference. It takes the CAMS forecast for
tomorrow, along with forecast weather and upwind fire detections,
and applies a correction fitted on this station's own history. The
output is one number: tomorrow's daily mean PM2.5 at Model Town.

## What counts as working

Raw CAMS is not the bar to beat, because almost anything beats it.
The honest bar is **persistence**: assuming tomorrow looks like the
most recent reading the station has published. The CPCB feed runs
behind, so that reading is a few days old when the forecast goes
out, and Pawan is always measured against persistence given the
same reading it had. The proposal set a 10% reduction in error
against it outside the burning season and 20% during it.

Both are met, the second across the 2025 and 2026 burning seasons,
and [Results](results.md) has the current figures, regenerated
every morning. The textbook version of persistence, which uses
yesterday's reading, still beats Pawan. Nobody has yesterday's
reading at forecast time, so it marks the cost of the publication
lag rather than a competitor, but it is reported rather than left
out.

See [Tomorrow's forecast](forecast.md) for the live service,
[Results](results.md) for the full evaluation, [Method](method.md)
for how it is measured and [Data](data.md) for what is in the
table. The [final report](https://github.com/Blakkbird/ucs503p-202627odd-Project-P1.v1/blob/master/project-report-final/main.pdf)
covers all of it in one place, and [Design](design.md) has the
requirements and diagrams.

## Layout

```
code/
  config.py        every setting, in one place
  ingest/          the daily job: observations, forecasts, fires
  features.py      daily.csv -> model rows, at a stated reading age
  model.py         ridge regression, standard library only
  evaluate.py      baselines, the walk-forward backtest, the range
  predict.py       tomorrow and the outlook, issued once and frozen
  candidates.py    every model on the leaderboard, one interface
  lab.py           the model lab and its shadow forecasts
  notify.py        the daily Telegram post
  api.py           the HTTP API, see API
  due.py           whether a backup run has work to do
  pages.py         renders the pages and the dashboard's data
  tests/
scripts/           one-off tools: history, backfill, the week 7
                   comparison, report figures
data/daily.csv     the whole dataset, one row per day
docs/              this site
journals/          weekly entries, one folder per member
```

## Running it

``` shell
pip install -r requirements.txt
python code/ingest/run_daily.py      # needs OPENAQ_KEY, FIRMS_MAP_KEY
python code/evaluate.py              # backtest, writes data/metrics.json
python code/predict.py               # tomorrow and the outlook
python code/lab.py                   # the model lab
python -m pytest code/tests/ -q
```

The forecast uses nothing outside the standard library.
`requirements.txt` carries pytest and ruff and nothing else. That
is deliberate: the daily job has to keep running unattended until
the end of the semester, and the least it can do is not depend on
something that might change underneath it. The model lab's
benchmarks need scikit-learn (`requirements-lab.txt`), and run in a
step of their own that cannot stop the daily commit.

The job runs every day through GitHub Actions and commits the
result, so `data/daily.csv` is the real dataset and its history is
the commit log.
