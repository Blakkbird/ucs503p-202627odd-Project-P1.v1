"""Tests for the HTTP API.

Each test points the API at files it writes itself, so the answers do
not depend on whatever the daily job committed this morning.
"""

import json
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import api
import config
import evaluate
import features

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_features import synthetic

TODAY = date(2026, 3, 30)
TOMORROW = TODAY + timedelta(days=1)


@pytest.fixture
def client(tmp_path, monkeypatch):
    rows = synthetic(90)
    samples = features.build(rows)
    ready = features.usable([s for s in samples if s.day < TOMORROW])
    fitted = evaluate.fit(ready)
    model_path = tmp_path / "model.json"
    evaluate.save_model(fitted, 2, model_path, samples=ready)
    target = next(s for s in samples if s.day == TOMORROW)

    def record(day, pm25, actual=None, horizon=None, issued=None):
        r = {"date": day.isoformat(),
             "issued": (issued or day - timedelta(days=1)).isoformat(),
             "issued_at": "2026-03-30T15:10+05:30", "pm25": pm25,
             "band": evaluate.band(pm25), "interval": [pm25 * 0.7,
                                                       pm25 * 1.5],
             "actual": actual,
             "error": None if actual is None else pm25 - actual}
        if horizon:
            r["horizon"] = horizon
        return r

    predictions = {
        "predictions": [record(TODAY - timedelta(days=2), 30.0, 28.0),
                        record(TODAY - timedelta(days=1), 32.0, 40.0),
                        record(TODAY, 35.0),
                        record(TOMORROW,
                               round(fitted.predict_one(target.x), 2))],
        "outlook": [record(TOMORROW + timedelta(days=1), 41.0, horizon=2,
                           issued=TODAY),
                    record(TODAY + timedelta(days=1), 99.0, horizon=2,
                           issued=TODAY - timedelta(days=1))],
        "status": {"target": TOMORROW.isoformat(), "issued": True,
                   "reason": None},
        "model": {"obs_age": 2}}
    board = {"backtest_on": "2026-03-28", "days": 40, "reference_age": 2,
             "models": [
                 {"key": "persistence", "label": "Persistence",
                  "kind": "baseline", "overall": {"mae": 10.0},
                  "skill": {"overall": 0.0, "burning": 0.0}},
                 {"key": "ridge", "label": "Ridge", "kind": "linear",
                  "shipped": True, "overall": {"mae": 8.0},
                  "skill": {"overall": 0.2, "burning": 0.1},
                  "verdict": "Shipped"}],
             "live": {"ridge": {"n": 5, "mae": 7.5}}}
    metrics = {"horizons": {"1": {"age": 2, "calibration": {
        "calm": {"low": -0.3, "high": 0.4, "errors": 300},
        "burning": {"low": -0.4, "high": 0.5, "errors": 60}}}}}

    for name, blob in (("predictions.json", predictions),
                       ("leaderboard.json", board),
                       ("metrics.json", metrics)):
        (tmp_path / name).write_text(json.dumps(blob))
    monkeypatch.setattr(config, "PREDICTIONS_JSON",
                        tmp_path / "predictions.json")
    monkeypatch.setattr(config, "LEADERBOARD_JSON",
                        tmp_path / "leaderboard.json")
    monkeypatch.setattr(config, "METRICS_JSON", tmp_path / "metrics.json")
    monkeypatch.setattr(config, "MODEL_JSON", model_path)
    monkeypatch.setattr(api, "today", lambda: TODAY)
    monkeypatch.setattr(api.features, "load", lambda path=None: rows)
    test = TestClient(api.app)
    test.target, test.fitted = target, fitted
    return test


def as_body(raw, **change):
    body = {"cams": raw["cams"], "reading": raw["obs_recent"],
            "temp": raw["temp"], "rh": raw["rh"],
            "wind_speed": raw["wind_speed"], "wind_dir": raw["wind_dir"],
            "fires": raw["fires"], "day": TOMORROW.isoformat()}
    return body | change


def test_the_index_lists_the_endpoints(client):
    got = client.get("/").json()
    assert "/forecast" in got["endpoints"] and got["docs"] == "/docs"


def test_tomorrow_comes_with_only_todays_outlook(client):
    got = client.get("/forecast").json()
    assert got["issued"] and got["target"] == TOMORROW.isoformat()
    assert got["forecast"]["band"] == evaluate.band(got["forecast"]["pm25"])
    assert got["advice"]
    assert [o["pm25"] for o in got["outlook"]] == [41.0]


def test_a_missing_forecast_says_why(client, tmp_path):
    blob = json.loads((tmp_path / "predictions.json").read_text())
    blob["predictions"] = blob["predictions"][:-1]
    blob["status"] = {"target": TOMORROW.isoformat(), "issued": False,
                      "reason": "the inputs for that day were not fetched"}
    (tmp_path / "predictions.json").write_text(json.dumps(blob))
    got = client.get("/forecast").json()
    assert not got["issued"] and got["forecast"] is None
    assert got["reason"] == "the inputs for that day were not fetched"


def test_the_record_filters_by_date_and_by_scoring(client):
    every = client.get("/forecasts").json()
    assert len(every) == 4
    scored = client.get("/forecasts", params={"scored": True}).json()
    assert [r["actual"] for r in scored] == [28.0, 40.0]
    since = client.get("/forecasts",
                       params={"start": TODAY.isoformat()}).json()
    assert [r["date"] for r in since] == [TODAY.isoformat(),
                                          TOMORROW.isoformat()]


def test_the_leaderboard_is_sorted_by_error(client):
    got = client.get("/models").json()
    assert [m["key"] for m in got["models"]] == ["ridge", "persistence"]
    assert got["models"][0]["live_days"] == 5


def test_health_reports_the_feed(client):
    got = client.get("/health").json()
    assert got["tomorrow_issued"] and got["model_reading_age"] == 2
    assert got["newest_reading"] and not got["stale"]


def test_whatif_reproduces_the_shipped_forecast(client):
    """The same inputs give the same number the job issued."""
    got = client.post("/whatif", json=as_body(client.target.raw)).json()
    assert got["pm25"] == pytest.approx(
        client.fitted.predict_one(client.target.x), abs=0.01)
    low, high = got["likely_range"]
    assert low < got["pm25"] < high


def mid(name):
    low, high = json.loads(config.MODEL_JSON.read_text())["ranges"][name]
    return (low + high) / 2


def test_whatif_inside_the_fitted_rows_flags_nothing(client):
    got = client.post("/whatif", json=as_body(
        client.target.raw, reading=mid("obs_recent"))).json()
    assert got["extrapolating"] == []


def test_whatif_flags_inputs_outside_the_fitted_rows(client):
    """Fires go into the model on a log scale, so a count far past
    anything seen can sit inside four standard deviations there.
    Flagging is done on the plain readings instead."""
    raw = client.target.raw
    got = client.post("/whatif", json=as_body(
        raw, reading=mid("obs_recent"), fires=20000)).json()
    flagged = {e["input"]: e for e in got["extrapolating"]}
    assert list(flagged) == ["fires"]
    assert flagged["fires"]["fitted_high"] < 20000


def test_whatif_refuses_impossible_inputs(client):
    raw = client.target.raw
    assert client.post("/whatif", json=as_body(raw, rh=150)).status_code \
        == 422
    assert client.post("/whatif",
                       json=as_body(raw, wind_dir=-5)).status_code == 422


def test_a_missing_file_is_a_503_that_names_it(client, monkeypatch,
                                                 tmp_path):
    monkeypatch.setattr(config, "LEADERBOARD_JSON", tmp_path / "nope.json")
    got = client.get("/models")
    assert got.status_code == 503 and "nope.json" in got.json()["detail"]


def test_the_model_file_keeps_its_fitted_ranges(client):
    blob = json.loads(config.MODEL_JSON.read_text())
    low, high = blob["ranges"]["fires"]
    assert 0 <= low <= high
