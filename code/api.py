"""Pawan's forecast as a small HTTP API.

The website is static on purpose: nothing has to stay running for it
to work, and a sleeping server cannot take it down. This API sits
beside it for programs rather than people. It serves the same data
files the site is built from, and adds the one thing a static page
cannot do for someone else: run the model on inputs they supply.

    pip install -r requirements-api.txt
    python code/api.py

Then open http://127.0.0.1:8000/docs for the interactive docs, which
FastAPI writes from the types below.

Every request reads the files fresh, so the answers move with the
daily job without a restart. Nothing here writes anything.
"""

import json
import math
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config
import evaluate
import features
from model import Ridge

# A what-if answer flags any input outside what the model was fitted
# on. Linear models keep extrapolating in a straight line long after
# the physics has stopped agreeing, and week 7's smoke model once
# forecast 2684 for a day that measured 13. The ranges come from
# model.json; a model file written before they were stored falls back
# to this many standard deviations, which is coarser.
EXTRAPOLATION_SD = 4.0

# What-if field names, against the names the readings have in the
# model's ranges.
FIELDS = {"cams": "cams", "reading": "obs_recent", "temp": "temp",
          "rh": "rh", "wind_speed": "wind_speed", "fires": "fires"}

app = FastAPI(
    title="Pawan",
    version="0.4.0",
    description=(
        "Next-day PM2.5 forecasts for the CPCB station at Model Town, "
        "Patiala. Every forecast is frozen when it is issued and scored "
        "when the station's reading for that day is published. Figures "
        "are in µg/m³, daily means, and bands follow the CPCB National "
        "AQI breakpoints for PM2.5. A student forecast for one station, "
        "not an official advisory."),
)


# --- reading the files -------------------------------------------

def load(path):
    """A data file, or a 503 saying which one is missing."""
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        raise HTTPException(503, f"{Path(path).name} has not been "
                                 "written yet; run the daily job") from None
    except json.JSONDecodeError:
        # The daily job rewrites files in place, so a request that
        # lands mid-write can see half a file. Try again shortly.
        raise HTTPException(503, f"{Path(path).name} is being "
                                 "rewritten; try again") from None


def today():
    return datetime.now(config.IST).date()


# --- response shapes ---------------------------------------------

Band = Literal["Good", "Satisfactory", "Moderate", "Poor", "Very Poor",
               "Severe"]


class Forecast(BaseModel):
    date: date
    issued: date
    issued_at: str | None = Field(
        None, description="When the job actually issued it, IST.")
    horizon: int = Field(1, description="Days ahead of the issue day.")
    pm25: float = Field(description="Forecast daily mean PM2.5.")
    band: Band
    likely_range: list[float] | None = Field(
        None, description="Sized so four days in five land inside it.")
    actual: float | None = Field(
        None, description="What the station measured, once published.")
    error: float | None = Field(
        None, description="Forecast minus measured.")


class Tomorrow(BaseModel):
    target: date
    issued: bool
    reason: str | None = Field(
        None, description="Why there is no forecast, when there is none.")
    forecast: Forecast | None
    advice: str | None
    outlook: list[Forecast] = Field(
        description="The two days after, from the same reading.")


class ModelRow(BaseModel):
    key: str
    label: str
    kind: str
    shipped: bool
    mae: float | None = Field(description="Backtest mean absolute error.")
    skill: float | None = Field(
        description="Error reduction against persistence, as a fraction.")
    burning_skill: float | None
    live_mae: float | None
    live_days: int | None
    verdict: str | None


class Models(BaseModel):
    backtest_on: date | None
    days: int | None
    reference_age: int | None
    models: list[ModelRow]


class Health(BaseModel):
    newest_reading: date | None
    reading_age_days: int | None
    last_forecast_for: date | None
    last_issued_at: str | None
    tomorrow_issued: bool
    reason: str | None
    model_reading_age: int | None
    stale: bool = Field(description="True when the station feed has "
                                    "gone quiet for longer than usual.")


class WhatIf(BaseModel):
    cams: float = Field(ge=0, le=2000, description="CAMS forecast PM2.5.")
    reading: float = Field(
        ge=0, le=2000,
        description="The station reading the forecast starts from.")
    temp: float = Field(ge=-10, le=55, description="Mean temperature, °C.")
    rh: float = Field(ge=0, le=100, description="Mean relative humidity, %.")
    wind_speed: float = Field(ge=0, le=150, description="Mean wind, km/h.")
    wind_dir: float = Field(ge=0, le=360,
                            description="Wind from, degrees (270 = west).")
    fires: float = Field(0, ge=0, le=20000,
                         description="Fires detected upwind the day before.")
    day: date | None = Field(
        None, description="The day being forecast; it decides whether "
                          "burning-season terms apply. Tomorrow if left out.")


class OutOfRange(BaseModel):
    input: str
    value: float
    fitted_low: float | None = Field(
        None, description="Lowest value in the rows the model was "
                          "fitted on.")
    fitted_high: float | None = None


class WhatIfAnswer(BaseModel):
    day: date
    pm25: float
    band: Band
    likely_range: list[float] | None
    extrapolating: list[OutOfRange] = Field(
        description="Inputs outside what the model was fitted on. Treat "
                    "the number with care when this is not empty.")
    model_reading_age: int | None = Field(
        description="The reading age the model was fitted for. A reading "
                    "of a different age is weighed as if it were this one.")


# --- endpoints ---------------------------------------------------

def as_forecast(record):
    return Forecast(date=record["date"], issued=record["issued"],
                    issued_at=record.get("issued_at"),
                    horizon=record.get("horizon", 1), pm25=record["pm25"],
                    band=record["band"],
                    likely_range=record.get("interval"),
                    actual=record.get("actual"), error=record.get("error"))


@app.get("/", summary="What is here")
def index():
    return {"name": "Pawan", "station": "Model Town, Patiala (CPCB)",
            "docs": "/docs",
            "endpoints": ["/forecast", "/forecasts", "/models", "/health",
                          "/whatif"],
            "site": config.SITE_URL}


@app.get("/forecast", response_model=Tomorrow,
         summary="Tomorrow's forecast and the two days after")
def forecast():
    blob = load(config.PREDICTIONS_JSON)
    tomorrow = today() + timedelta(days=1)
    record = next((r for r in blob.get("predictions", [])
                   if r["date"] == tomorrow.isoformat()), None)
    status = blob.get("status") or {}
    later = [as_forecast(r) for r in sorted(
        blob.get("outlook", []), key=lambda r: r["horizon"])
        if r.get("issued") == today().isoformat()]
    reason = None
    if record is None:
        reason = (status.get("reason")
                  if status.get("target") == tomorrow.isoformat()
                  else "today's run has not happened yet")
    return Tomorrow(
        target=tomorrow, issued=record is not None, reason=reason,
        forecast=as_forecast(record) if record else None,
        advice=pages_advice(record["band"]) if record else None,
        outlook=later)


@app.get("/forecasts", response_model=list[Forecast],
         summary="Every forecast on record, with what was measured")
def forecasts(start: date | None = None, end: date | None = None,
              scored: bool = Query(
                  False, description="Only days the station has reported."),
              limit: int = Query(100, ge=1, le=1000)):
    blob = load(config.PREDICTIONS_JSON)
    out = []
    for r in blob.get("predictions", []):
        day = date.fromisoformat(r["date"])
        if start and day < start or end and day > end:
            continue
        if scored and r.get("actual") is None:
            continue
        out.append(as_forecast(r))
    return out[-limit:]


@app.get("/models", response_model=Models,
         summary="The model lab's leaderboard")
def models():
    board = load(config.LEADERBOARD_JSON)
    live = board.get("live") or {}
    rows = []
    for m in board.get("models", []):
        overall, sk = m.get("overall") or {}, m.get("skill") or {}
        got = live.get(m["key"]) or {}
        rows.append(ModelRow(
            key=m["key"], label=m["label"], kind=m["kind"],
            shipped=bool(m.get("shipped")), mae=overall.get("mae"),
            skill=sk.get("overall"), burning_skill=sk.get("burning"),
            live_mae=got.get("mae"), live_days=got.get("n"),
            verdict=m.get("verdict")))
    rows.sort(key=lambda r: math.inf if r.mae is None else r.mae)
    return Models(backtest_on=board.get("backtest_on"),
                  days=board.get("days"),
                  reference_age=board.get("reference_age"), models=rows)


@app.get("/health", response_model=Health,
         summary="Whether the pipeline is keeping up")
def health():
    blob = load(config.PREDICTIONS_JSON)
    rows = features.load()
    newest = max((k for k, r in rows.items() if r.get("obs_pm25")),
                 default=None)
    age = (today() - date.fromisoformat(newest)).days if newest else None
    records = blob.get("predictions", [])
    last = records[-1] if records else {}
    status = blob.get("status") or {}
    tomorrow = (today() + timedelta(days=1)).isoformat()
    model = (blob.get("model") or {})
    return Health(
        newest_reading=newest, reading_age_days=age,
        last_forecast_for=last.get("date"),
        last_issued_at=last.get("issued_at"),
        tomorrow_issued=any(r["date"] == tomorrow for r in records),
        reason=status.get("reason") if status.get("target") == tomorrow
        else None,
        model_reading_age=model.get("obs_age"),
        stale=age is None or age > config.OBS_STALENESS_LIMIT_DAYS)


@app.post("/whatif", response_model=WhatIfAnswer,
          summary="Run the shipped model on your own inputs")
def whatif(inputs: WhatIf):
    blob = load(config.MODEL_JSON)
    model = Ridge.from_dict(blob)
    day = inputs.day or today() + timedelta(days=1)
    raw = {"cams": inputs.cams, "obs_recent": inputs.reading,
           "temp": inputs.temp, "rh": inputs.rh,
           "wind_speed": inputs.wind_speed, "wind_dir": inputs.wind_dir,
           "fires": inputs.fires}
    burning = day.month in config.BURNING_MONTHS
    x = features.transform(raw, burning, model.names)
    point = max(model.predict_one(x), 0.0)

    far = outside(inputs, blob, x, model)

    metrics = load(config.METRICS_JSON)
    block = ((metrics.get("horizons") or {}).get("1") or {})
    span = evaluate.likely_range(point, block.get("calibration"), burning)
    return WhatIfAnswer(
        day=day, pm25=round(point, 2), band=evaluate.band(point),
        likely_range=[round(v, 2) for v in span] if span else None,
        extrapolating=far, model_reading_age=blob.get("obs_age"))


def outside(inputs, blob, x, model):
    """The inputs that lie outside what the model was fitted on."""
    ranges = blob.get("ranges")
    if ranges:
        far = []
        for field, name in FIELDS.items():
            value, span = getattr(inputs, field), ranges.get(name)
            if span and not span[0] <= value <= span[1]:
                far.append(OutOfRange(input=field, value=value,
                                      fitted_low=span[0],
                                      fitted_high=span[1]))
        return far

    # An older model file: fall back to spread, on the model's own
    # (partly logged) inputs, mapped back to the field they came from.
    source = {"cams_log": "cams", "obs_recent_log": "reading",
              "temp": "temp", "rh": "rh", "wind_speed": "wind_speed",
              "wind_u": "wind_dir", "wind_v": "wind_dir",
              "fire_log": "fires"}
    far, seen = [], set()
    for name, value, mean, dev in zip(model.names, x, model.means,
                                      model.devs):
        field = source.get(name)
        if field and field not in seen and dev and \
                abs(value - mean) / dev > EXTRAPOLATION_SD:
            seen.add(field)
            far.append(OutOfRange(input=field,
                                  value=getattr(inputs, field)))
    return far


def pages_advice(band):
    # The dashboard's wording, so the API and the page say the same.
    import pages
    return pages.ADVICE.get(band)


def main():
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
