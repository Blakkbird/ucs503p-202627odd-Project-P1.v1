# scripts

One-time setup and analysis. None of these run in CI; the daily
pipeline is `code/ingest/run_daily.py`, driven by
`.github/workflows/ingest.yml`.

They are kept in the repo so the numbers quoted in the proposal
can be reproduced.

| script | purpose | run |
|---|---|---|
| `find_station.py` | find OpenAQ location and sensor ids near the configured coordinates | once, or when changing station |
| `check_sensor.py` | compare candidate sensors, report which is live | once, or if readings go stale |
| `bootstrap.py` | pull history, print baseline errors, seed `data/daily.csv` | once |
| `diagnose.py` | bias, correlation, and how much a rescale removes | after bootstrap, and again after the season |

All need `OPENAQ_KEY` in `.env`. `run_daily.py` also needs
`FIRMS_MAP_KEY`.
