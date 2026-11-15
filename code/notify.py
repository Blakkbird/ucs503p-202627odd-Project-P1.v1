"""Post tomorrow's forecast to a Telegram channel.

Run by the daily workflow once the forecast is out. It needs two
repository secrets, TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID (the
channel's @name). Without them it prints the message it would have
sent and exits cleanly, so the step costs nothing until a channel
exists.

Three rules hold it in place.

One post per forecast. The workflow can run more than once a day: a
manual run after a merge, or a rerun of a failed job. A channel that
repeats itself is a channel people mute. data/notify.json records
what was last posted, and the same forecast is never posted twice.

Say so when there is no forecast. Silence on a bad morning looks the
same as a quiet one, so the channel gets a short note with the
reason instead, and the forecast still goes out if a later run
manages one.

Never print the token. The Bot API puts the token in the URL, and
an error that quotes a URL cut at sixty characters prints most of a
token. GitHub masks a secret in its public logs only where the whole
value appears, so a cut-off one slips straight through. The ingest's
fetch() now takes its keys out of a URL before quoting it; here the
URL is never quoted at all, and errors name the status and nothing
else.
"""

import json
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config
import pages

API = "https://api.telegram.org"
TIMEOUT = 30


class NotifyError(Exception):
    """Telegram could not be reached, or said no. Never holds the URL."""


def day_name(iso):
    d = date.fromisoformat(iso)
    return f"{d:%A} {d.day} {d:%B}"


def channel_link(chat_id):
    """The public link for a channel named by its @handle, else None."""
    chat_id = (chat_id or "").strip()
    if chat_id.startswith("@") and len(chat_id) > 1:
        return f"https://t.me/{chat_id[1:]}"
    return None


def compose(predictions, today):
    """(key, text) for today's post, or None when there is nothing.

    The key is the target date and whether a forecast went out, so a
    later run that does issue one still gets to post it.
    """
    tomorrow = (today + timedelta(days=1)).isoformat()
    records = (predictions or {}).get("predictions", [])
    record = next((r for r in records if r["date"] == tomorrow), None)
    dashboard = f"{config.SITE_URL}/dashboard/"

    if record is None:
        status = (predictions or {}).get("status") or {}
        if status.get("target") != tomorrow:
            return None  # this morning's forecast step never ran
        reason = status.get("reason") or "the daily job could not run"
        text = (f"No forecast for {day_name(tomorrow)}: {reason}.\n\n"
                f"It usually clears on the next day's run. {dashboard}")
        return (f"{tomorrow}|missing", text)

    band = record["band"]
    lines = []
    if band in ("Poor", "Very Poor", "Severe"):
        lines.append(f"Air quality warning for Patiala: {band} expected.")
    lines.append(f"Pawan forecast for {day_name(tomorrow)}, "
                 f"Model Town, Patiala")
    lines.append("")
    lines.append(f"PM2.5: {record['pm25']:.0f} µg/m³, {band}")
    if record.get("interval"):
        low, high = record["interval"]
        lines.append(f"Likely between {low:.0f} and {high:.0f}")
    lines.append("")
    lines.append(pages.ADVICE.get(band, ""))

    later = [r for r in (predictions or {}).get("outlook", [])
             if r.get("issued") == today.isoformat()]
    if later:
        lines.append("")
        lines.append("After that:")
        for r in sorted(later, key=lambda r: r["horizon"]):
            lines.append(f"{day_name(r['date'])}: {r['pm25']:.0f}, "
                         f"{r['band']}")

    inputs = record.get("inputs") or {}
    basis = []
    if inputs.get("obs_day") and inputs.get("persistence_operational"):
        basis.append(f"the station's reading for "
                     f"{day_name(inputs['obs_day'])} "
                     f"({inputs['persistence_operational']:.0f})")
    if inputs.get("cams_pm25"):
        basis.append(f"the CAMS forecast ({inputs['cams_pm25']:.0f})")
    if basis:
        lines.append("")
        lines.append("Built from " + " and ".join(basis)
                     + ", corrected for this station.")
    lines.append("")
    lines.append(f"Details: {dashboard}")
    lines.append("A student forecast for one station, not an official "
                 "advisory.")
    return (f"{tomorrow}|forecast", "\n".join(lines))


def send(token, chat_id, text, opener=urllib.request.urlopen):
    """Post `text` to the chat. Raises NotifyError, never quoting the URL.

    `opener` is a parameter so the tests can stand in for the
    network, including a failing one.
    """
    body = json.dumps({"chat_id": chat_id, "text": text,
                       "disable_web_page_preview": True}).encode()
    req = urllib.request.Request(
        f"{API}/bot{token}/sendMessage", data=body,
        headers={"Content-Type": "application/json"})
    try:
        with opener(req, timeout=TIMEOUT) as r:
            answer = json.loads(r.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as e:
        # 401 is a wrong token, 400 usually a wrong chat or a bot that
        # is not an admin of the channel. Status only: the exception's
        # own text carries the URL, and with it the token.
        raise NotifyError(f"Telegram answered HTTP {e.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise NotifyError(f"could not reach Telegram "
                          f"({type(e).__name__})") from None
    except json.JSONDecodeError:
        raise NotifyError("Telegram's answer was not JSON") from None
    if not answer.get("ok"):
        raise NotifyError(f"Telegram refused the message: "
                          f"{answer.get('description', 'no reason given')}")
    return answer


def load(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def main():
    today = datetime.now(config.IST).date()
    predictions = load(config.PREDICTIONS_JSON)
    composed = compose(predictions, today)
    if composed is None:
        print("nothing to post: this morning's forecast step did not run")
        return 0
    key, text = composed

    record = load(config.NOTIFY_JSON)
    if record.get("last") == key and "--force" not in sys.argv:
        print(f"already posted {key}, not posting it again")
        return 0

    token = config.TELEGRAM_BOT_TOKEN
    chat = config.TELEGRAM_CHAT_ID
    if not token or not chat:
        print("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is not set; "
              "this is what would have been posted:\n")
        print(text)
        return 0

    try:
        send(token, chat, text)
    except NotifyError as e:
        print(f"ERROR: not posted: {e}")
        return 1

    record = {"last": key,
              "sent_at": datetime.now(config.IST).isoformat(
                  timespec="seconds"),
              "channel": channel_link(chat)}
    with open(config.NOTIFY_JSON, "w") as f:
        json.dump(record, f, indent=1)
    print(f"posted {key}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
