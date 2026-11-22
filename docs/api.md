# API

The website is static on purpose. Nothing has to stay running for it
to work, and a sleeping server cannot take it down. The API sits
beside it for programs rather than people: it serves the same data
files the site is built from, and does the one thing a static page
cannot do for someone else, which is run the model on inputs they
supply.

It is written with [FastAPI](https://fastapi.tiangolo.com/), which
builds the interactive documentation from the code's own types.

## Running it

``` shell
pip install -r requirements-api.txt
python code/api.py
```

Then open <http://127.0.0.1:8000/docs>. Each endpoint can be tried
from that page.

Every request reads the files in `data/` fresh, so the answers move
with the daily job without a restart. The API never writes anything.

## Endpoints

| Method | Path | What it returns |
| --- | --- | --- |
| GET | `/forecast` | Tomorrow's forecast, its likely range and advice, and the two days after. If there is no forecast, the reason. |
| GET | `/forecasts` | Every forecast on record with what was measured. Filters: `start`, `end`, `scored`, `limit`. |
| GET | `/models` | The model lab's leaderboard, best backtest error first, with each model's live record. |
| GET | `/health` | The newest station reading and how old it is, the last forecast and when it was issued, and whether the feed has gone stale. |
| POST | `/whatif` | The shipped model's forecast for inputs you supply. |

All figures are daily mean PM2.5 in µg/m³. Bands follow the CPCB
National AQI breakpoints.

## What if

`/whatif` takes the same readings the daily forecast is built from:

``` json
{
  "cams": 65.2,
  "reading": 68.8,
  "temp": 19.58,
  "rh": 62.08,
  "wind_speed": 9.49,
  "wind_dir": 311.91,
  "fires": 123,
  "day": "2026-11-16"
}
```

These are 16 November's real inputs, and the answer is the forecast
the daily job issued for that day, to the hundredth:

``` json
{
  "day": "2026-11-16",
  "pm25": 52.53,
  "band": "Satisfactory",
  "likely_range": [34.06, 91.24],
  "extrapolating": [],
  "model_reading_age": 2
}
```

Two kinds of input are treated differently.

- **Impossible inputs** are refused with a 422: humidity above 100%,
  a negative fire count, a bearing outside 0 to 360.
- **Inputs outside what the model was fitted on** are answered, but
  listed under `extrapolating`, with the lowest and highest value in
  the fitted rows. A linear model keeps going in a straight line long
  after the physics stops agreeing, so a number built on these
  deserves suspicion. Asked about 20,000 fires, ten times anything in
  the record, the model still says Moderate, and the answer says why
  not to trust it.

`model_reading_age` is the age of station reading the model was
fitted for, counted from the day forecast. A reading of another age
is weighed as if it were that one; see [Method](method.md).
