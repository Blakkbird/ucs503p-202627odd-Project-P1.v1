![Tiet Logo](assets/tiet-logo.svg){ .tiet-logo }

**UCS503: Software Engineering (Project)**  
**TIET Patiala**

# Pawan: Next-Day Air Quality Forecasting for Patiala

**Author(s)**:

`(GS)` Gurkirpa Singh `<gsarao_be24 -at- thapar -dot- edu>`  
`(KB)` Ketubh Bansal `(1024170399)`  
`(AK)` Aayush Kandhol `(1024170379)`

**Instructor**: Dr. Paramveer Kaur

## What this is

A global atmospheric model called CAMS publishes a PM2.5 forecast
for every point on Earth, Patiala included. At the CPCB station in
Model Town it is badly wrong. Over the 118 days we have measured
it predicted a mean of 74 ug/m3 against an observed mean of 23, an
average error of 51 ug/m3, and it tracks the day-to-day movement
at only r = 0.42.

That is not surprising. CAMS global runs on a 0.4 degree grid,
roughly 45 km per cell, so a single number covers Patiala and
everything around it. What it cannot know is what this particular
station reads.

Pawan learns that difference. It takes the CAMS forecast for
tomorrow, along with local weather and upwind fire detections, and
applies a correction fitted on this station's own history. The
output is one number: tomorrow's daily mean PM2.5 at Model Town.

## What counts as working

Raw CAMS is not the bar to beat, because almost anything beats it.
The honest bar is **persistence** -- assuming tomorrow looks like
the most recent reading the station has published. On the current
record that scores an MAE of about 4.6 ug/m3, and through the calm
months it is hard to improve on. Pawan currently sits at 3.3,
which is 28% better.

Two versions of persistence get quoted in this project and they
are not interchangeable. The 4.6 above is the operational one,
using the freshest reading actually available when the forecast
goes out -- about four days old, because the CPCB feed publishes
late. The textbook version uses yesterday's reading, which nobody
has yet at that point, and scores 3.5. The gap between them is the
cost of the publication lag rather than anything a model can fix.

The targets set in the proposal are a 10% reduction against
persistence outside the burning season and 20% during it. Paddy
residue burning upwind through October and November is when the
daily mean actually moves, when persistence breaks down, and when
a forecast is worth having. Nothing in the record so far covers
that season, so the second target is still untested.

See [Tomorrow's forecast](forecast.md) for the live service,
[Results](results.md) for the full evaluation, [Method](method.md)
for how it is measured and [Data](data.md) for what is in the
table.

## Layout

```
code/
  config.py        every setting, in one place
  ingest/          the daily job: observations, forecast, fires
  features.py      daily.csv -> model-ready rows
  model.py         ridge regression, standard library only
  evaluate.py      baselines and the walk-forward backtest
  predict.py       issues tomorrow's forecast, once, and freezes it
  pages.py         renders forecast.md and results.md from the data
  tests/
scripts/           one-off tools: bootstrap, backfill, diagnostics
data/daily.csv     the whole dataset, one row per day
docs/              this site
journals/          weekly entries, one folder per member
```

## Running it

``` shell
pip install -r requirements.txt
python code/ingest/run_daily.py      # needs OPENAQ_KEY, FIRMS_MAP_KEY
python code/evaluate.py              # backtest, writes data/metrics.json
python -m pytest code/tests/ -q
```

The ingest and the model use nothing outside the standard library.
`requirements.txt` carries pytest and ruff and nothing else. That
is deliberate: the daily job has to keep running unattended until
November, and the least it can do is not depend on something that
might change underneath it.

Ingest runs every morning through GitHub Actions and commits the
result, so `data/daily.csv` is the real dataset and its history is
the commit log.
