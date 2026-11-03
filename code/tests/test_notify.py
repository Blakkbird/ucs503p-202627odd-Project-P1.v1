"""Tests for the Telegram post.

The one that matters most is about the token. The Bot API carries it
in the URL, Python's own errors quote the URL, and GitHub only masks
a secret where the whole value appears in a log. So every failure
path is checked for any piece of the token, not just all of it.
"""

import io
import json
import sys
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config
import notify
import pages

TOKEN = "7123456789:AAHf3kQx_FAKE-TOKEN-ONLY-FOR-THIS-TEST-0123"


def predictions(today, pm25=66.0, band="Moderate", outlook=True):
    tomorrow = (today + timedelta(days=1)).isoformat()
    blob = {"predictions": [{
        "date": tomorrow, "issued": today.isoformat(), "pm25": pm25,
        "band": band, "interval": [42.0, 112.0],
        "inputs": {"obs_day": (today - timedelta(days=1)).isoformat(),
                   "persistence_operational": 106.0, "cams_pm25": 93.4}}],
        "status": {"target": tomorrow, "issued": True, "reason": None}}
    if outlook:
        blob["outlook"] = [
            {"date": (today + timedelta(days=h)).isoformat(), "horizon": h,
             "issued": today.isoformat(), "pm25": 70.0 - h,
             "band": "Moderate"} for h in (3, 2)]
    return blob


def test_the_post_says_what_the_dashboard_says():
    today = datetime(2026, 11, 3).date()
    key, text = notify.compose(predictions(today), today)
    assert key == "2026-11-04|forecast"
    assert "Wednesday 4 November" in text
    assert "66 µg/m³, Moderate" in text
    assert "Likely between 42 and 112" in text
    assert pages.ADVICE["Moderate"] in text
    assert text.index("Thursday 5 November") < text.index("Friday 6 November")
    assert "not an official advisory" in text
    assert "warning" not in text.lower()


def test_a_poor_day_leads_with_a_warning():
    today = datetime(2026, 11, 3).date()
    _, text = notify.compose(predictions(today, 104.0, "Poor"), today)
    assert text.startswith("Air quality warning for Patiala: Poor")


def test_no_forecast_is_posted_as_no_forecast():
    today = datetime(2026, 11, 3).date()
    blob = {"predictions": [], "status": {
        "target": "2026-11-04", "issued": False,
        "reason": "the inputs for that day were not fetched"}}
    key, text = notify.compose(blob, today)
    assert key == "2026-11-04|missing"
    assert text.startswith("No forecast for Wednesday 4 November: the "
                           "inputs for that day were not fetched.")


def test_nothing_is_posted_when_the_forecast_step_never_ran():
    today = datetime(2026, 11, 3).date()
    blob = {"predictions": [], "status": {"target": "2026-11-01"}}
    assert notify.compose(blob, today) is None


def leaks(message):
    """The longest piece of the token, from its start, in `message`."""
    return max(k for k in range(len(TOKEN) + 1) if TOKEN[:k] in message)


def test_an_http_error_never_carries_the_token():
    def refuse(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized",
                                     {}, io.BytesIO(b""))
    try:
        notify.send(TOKEN, "@pawan_test", "hi", opener=refuse)
    except notify.NotifyError as e:
        assert str(e) == "Telegram answered HTTP 401"
        assert leaks(str(e)) == 0
        assert e.__cause__ is None and e.__suppress_context__
    else:
        raise AssertionError("a refusal should raise")


def test_a_network_failure_never_carries_the_token():
    def unreachable(req, timeout=None):
        raise urllib.error.URLError(f"no route to {req.full_url}")
    try:
        notify.send(TOKEN, "@pawan_test", "hi", opener=unreachable)
    except notify.NotifyError as e:
        assert leaks(str(e)) == 0
        assert "URLError" in str(e)


class Answer:
    def __init__(self, blob):
        self.body = json.dumps(blob).encode()

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_a_sent_post_carries_the_chat_and_the_text():
    seen = {}

    def accept(req, timeout=None):
        seen["body"] = json.loads(req.data)
        return Answer({"ok": True})
    notify.send(TOKEN, "@pawan_test", "hello", opener=accept)
    assert seen["body"]["chat_id"] == "@pawan_test"
    assert seen["body"]["text"] == "hello"


def test_a_refusal_in_the_answer_is_reported():
    def refuse(req, timeout=None):
        return Answer({"ok": False, "description": "chat not found"})
    try:
        notify.send(TOKEN, "@nope", "hi", opener=refuse)
    except notify.NotifyError as e:
        assert "chat not found" in str(e)


def test_the_same_forecast_is_posted_once(tmp_path, monkeypatch):
    today = datetime.now(config.IST).date()
    pred = tmp_path / "predictions.json"
    pred.write_text(json.dumps(predictions(today)))
    record = tmp_path / "notify.json"
    monkeypatch.setattr(config, "PREDICTIONS_JSON", pred)
    monkeypatch.setattr(config, "NOTIFY_JSON", record)
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", TOKEN)
    monkeypatch.setattr(config, "TELEGRAM_CHAT_ID", "@pawan_test")
    monkeypatch.setattr(sys, "argv", ["notify.py"])
    sent = []
    monkeypatch.setattr(notify, "send", lambda t, c, text: sent.append(text))

    assert notify.main() == 0
    assert notify.main() == 0
    assert len(sent) == 1
    saved = json.loads(record.read_text())
    assert saved["channel"] == "https://t.me/pawan_test"
    assert saved["last"].endswith("|forecast")


def test_a_forecast_after_a_missing_morning_still_goes_out(tmp_path,
                                                            monkeypatch):
    today = datetime.now(config.IST).date()
    tomorrow = (today + timedelta(days=1)).isoformat()
    pred = tmp_path / "predictions.json"
    pred.write_text(json.dumps(predictions(today)))
    record = tmp_path / "notify.json"
    record.write_text(json.dumps({"last": f"{tomorrow}|missing"}))
    monkeypatch.setattr(config, "PREDICTIONS_JSON", pred)
    monkeypatch.setattr(config, "NOTIFY_JSON", record)
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", TOKEN)
    monkeypatch.setattr(config, "TELEGRAM_CHAT_ID", "@pawan_test")
    monkeypatch.setattr(sys, "argv", ["notify.py"])
    sent = []
    monkeypatch.setattr(notify, "send", lambda t, c, text: sent.append(text))
    assert notify.main() == 0
    assert len(sent) == 1


def test_without_secrets_it_only_prints(tmp_path, monkeypatch, capsys):
    today = datetime.now(config.IST).date()
    pred = tmp_path / "predictions.json"
    pred.write_text(json.dumps(predictions(today)))
    monkeypatch.setattr(config, "PREDICTIONS_JSON", pred)
    monkeypatch.setattr(config, "NOTIFY_JSON", tmp_path / "notify.json")
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setattr(config, "TELEGRAM_CHAT_ID", "")
    monkeypatch.setattr(sys, "argv", ["notify.py"])
    assert notify.main() == 0
    assert "would have been posted" in capsys.readouterr().out
    assert not (tmp_path / "notify.json").exists()


def test_a_channel_link_comes_only_from_a_public_name():
    assert notify.channel_link("@pawan_patiala") == "https://t.me/pawan_patiala"
    assert notify.channel_link("-1001234567890") is None
    assert notify.channel_link("") is None


def test_the_badge_reads_the_headline_skill():
    good = pages.badge({"skill": {"operational": 0.146}})
    assert good["message"] == "14.6% better" and good["schemaVersion"] == 1
    bad = pages.badge({"skill": {"operational": -0.05}})
    assert bad["message"] == "5.0% worse"
    assert pages.badge(None)["message"] == "not scored yet"
