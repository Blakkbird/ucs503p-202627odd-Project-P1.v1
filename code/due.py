"""Decide whether a scheduled run of the daily job has work to do.

The daily job has one morning run and four backups through the day.
It needs them. GitHub starts the 08:00 IST run seven to eight hours
late, and in the week from 15 November five of seven morning runs
failed on the weather source: once busy (HTTP 429), four times with
TLS handshakes that never completed. Four days went without a
forecast. A failure like that clears with time, and with a fresh
runner on a different IP address, which is what a later run is.

A backup only does the work in two cases:

  * today's run has already happened and went out without a
    forecast for tomorrow (predict.py records that in its status);
  * it is evening, and there is still no sign of today's run, as
    when GitHub drops a scheduled run altogether.

Otherwise it stands down in a few seconds and makes no commit. The
first rule matters because GitHub's delays are not steady: a backup
that happens to fire on time could otherwise beat the morning run
and issue tomorrow's forecast from a staler reading.

Runs started by hand always go ahead.

    python code/due.py      prints needed=true or needed=false, and
                            writes it to $GITHUB_OUTPUT when set
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config

# Must match the first cron line in .github/workflows/ingest.yml.
MORNING = "30 2 * * *"

# From this hour, IST, a backup stops waiting for a morning run that
# has left no trace, and does the work itself.
EVENING_HOUR = 18


def needed(predictions, now, event, schedule):
    """(True or False, the reason in a few words)."""
    if event != "schedule":
        return True, f"started by {event or 'hand'}"
    if schedule == MORNING:
        return True, "the morning run"
    predictions = predictions or {}
    tomorrow = (now.date() + timedelta(days=1)).isoformat()
    issued = {r.get("date") for r in predictions.get("predictions", [])}
    if tomorrow in issued:
        return False, f"the forecast for {tomorrow} is already out"
    status = predictions.get("status") or {}
    if status.get("target") == tomorrow:
        return True, (f"today's run left no forecast for {tomorrow}: "
                      f"{status.get('reason') or 'no reason given'}")
    if now.hour >= EVENING_HOUR:
        return True, f"evening, and still no run for {tomorrow}"
    return False, "waiting for today's run"


def main():
    try:
        with open(config.PREDICTIONS_JSON) as f:
            predictions = json.load(f)
    except (OSError, json.JSONDecodeError):
        predictions = {}
    run, why = needed(predictions, datetime.now(config.IST),
                      os.environ.get("EVENT", ""),
                      os.environ.get("SCHEDULE", ""))
    print(f"needed={'true' if run else 'false'}: {why}")
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write(f"needed={'true' if run else 'false'}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
