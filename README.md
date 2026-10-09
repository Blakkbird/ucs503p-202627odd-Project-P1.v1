# Pawan: next-day air quality forecasting for Patiala

Pawan issues a forecast of tomorrow's daily mean PM2.5 at the CPCB
station in Model Town, Patiala, every morning, without anyone
running it. It takes the CAMS global forecast, which overshoots
badly at this station, and corrects it using the station's own
history, forecast weather and satellite fire detections upwind.

**[Tomorrow's forecast](https://blakkbird.github.io/ucs503p-202627odd-Project-P1.v1/forecast/)** ·
**[Results](https://blakkbird.github.io/ucs503p-202627odd-Project-P1.v1/results/)** ·
**[Project page](https://blakkbird.github.io/ucs503p-202627odd-Project-P1.v1/)** ·
[Proposal](project-proposal/main.pdf) ·
[Prototype report](project-report-prototype-stage/main.pdf)

UCS503P Software Engineering, TIET Patiala, 2026-27 odd semester.
Instructor: Dr. Paramveer Kaur.

## Where it stands

Walk-forward backtest, April 2025 to October 2026, mean absolute
error in µg/m³. Skill is the reduction against operational
persistence, which is the freshest reading the station has
actually published when the forecast goes out.

| | Days | Pawan | Persistence | Raw CAMS | Skill | Target |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Calm season | 425 | 8.11 | 11.35 | 43.89 | +28.5% | 10% |
| Burning season (Oct, Nov) | 63 | 12.16 | 19.14 | 28.21 | +36.5% | 20% |
| Live forecasts only | 47 | 4.33 | 7.50 | 41.17 | +42.3% | |

Snapshot from 10 October 2026. The [results page](https://blakkbird.github.io/ucs503p-202627odd-Project-P1.v1/results/)
is regenerated every morning and is the current one.

What it does not do yet: beat persistence from *yesterday's*
reading, which nobody has at forecast time, or see pollution
spikes coming. Both are measured, explained and planned for in the
[prototype report](project-report-prototype-stage/main.pdf).

## How it works

Once a day, at 08:00 IST, a GitHub Actions job:

1. fetches the last 30 days of station readings (OpenAQ), tomorrow's
   CAMS and weather forecasts (Open-Meteo), and fire detections
   (NASA FIRMS), and appends them to `data/daily.csv`;
2. refits the model from scratch and re-runs the walk-forward
   backtest (`code/evaluate.py`);
3. issues tomorrow's forecast and freezes it (`code/predict.py`);
4. rebuilds the forecast and results pages from the data
   (`code/pages.py`);
5. runs the full test suite, and only then commits.

There is no server and no database. The dataset is a CSV in git,
so its history is the commit log, and every number on the site is
generated from it. The model is a ridge regression in log space,
about eighty lines, standard library only. Why it is built this
way is in [Method](docs/method.md); what is in the table and where
it comes from is in [Data](docs/data.md).

## Layout

```
code/
  config.py          every setting, in one place
  ingest/            the daily job: observations, forecast, fires
  features.py        daily.csv -> model rows, and the leakage rules
  model.py           ridge regression, by hand
  evaluate.py        baselines and the walk-forward backtest
  predict.py         issues tomorrow's forecast, once, and freezes it
  pages.py           renders forecast.md and results.md
  tests/             100 tests, run on every PR and every data commit
scripts/
  extend_history.py  pulls the record back to the sensor's start
  backfill_history.py  weather and fire counts for archive rows
  compare_models.py  backtests candidate models side by side
  report_figures.py  every number in the prototype report
data/                daily.csv, model.json, metrics.json, predictions.json
docs/                the project page (MkDocs)
journals/            weekly entries, one folder per member
project-proposal/              LaTeX, week 4
project-report-prototype-stage/  LaTeX, week 7
project-report-final/          LaTeX, week 17
```

## Running it

```shell
pip install -r requirements.txt
python code/ingest/run_daily.py     # needs OPENAQ_KEY and FIRMS_MAP_KEY
python code/evaluate.py             # backtest; writes data/metrics.json
python code/predict.py              # tomorrow's forecast
python code/pages.py                # docs/forecast.md, docs/results.md
python -m pytest code/tests/ -q
```

Keys can go in a `.env` file at the root; it is gitignored. Nothing
outside the standard library is needed to run the pipeline.
`requirements.txt` carries `pytest` and `ruff` and nothing else, on
purpose: the daily job has to keep running unattended, and the less
it depends on, the less can change underneath it.

To rebuild the prototype report:

```shell
python scripts/report_figures.py
cd project-report-prototype-stage
latexmk -pdf main.tex
```

## Workflows

| Workflow | When | What |
| --- | --- | --- |
| CI | every PR | `ruff` and `pytest` |
| Daily ingest | 08:00 IST | the five steps above, then commit |
| mkdocs | every push to `master` | build and deploy the project page |
| Extend history | by hand, dry run by default | one-off history extension |

`master` is protected. Changes go through pull requests.

## Team

| | Roll No |
| --- | --- |
| Gurkirpa Singh | 1024170378 |
| Ketubh Bansal | 1024170399 |
| Aayush Kandhol | 1024170379 |

Forked from the course template,
[tiet-ucs503/ucs503p-202627odd-template](https://github.com/tiet-ucs503/ucs503p-202627odd-template).
