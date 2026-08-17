"""Fill the weather and fire columns for days already in daily.csv.

The daily job only ever writes tomorrow's row, and the weather
columns were added to it after scripts/bootstrap.py had already
seeded three months of history. The result is a table with good
observations, good CAMS values, and almost no meteorology -- which
means no model can use meteorology. This fills the hole once.

Safe to re-run: a cell that already has a value is never touched,
so a partial run can simply be repeated.

    python scripts/backfill_history.py            # do it
    python scripts/backfill_history.py --dry-run  # just report
    python scripts/backfill_history.py --force    # redo the weather

Weather comes from an archive of past forecast runs rather than
from a reanalysis, because the model has to be fitted on the same
kind of number it will be fed in production. Three archives are
tried in order, best provenance first:

  1. Previous Runs, which serves each variable at a fixed lead
     time. `_previous_day1` is the value predicted 24 hours before
     the day it describes, which is very close to what the live
     job records at 09:00 the day before.
  2. the Historical Forecast archive, which stitches the opening
     hours of each successive run into one series. Closer to
     observed conditions, so slightly optimistic as a stand-in for
     a forecast -- acceptable, but worth knowing about.
  3. the ordinary forecast endpoint, which serves the same
     stitched series but only 92 days back. Same caveat as (2),
     plus it cannot reach the oldest rows. It is here because it
     is the host the daily job already uses, so it is the one
     least likely to be down when the others are.

Whichever one answers is printed and noted in the journal, because
it changes how the numbers should be read.
"""

import argparse
import csv
import json
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))
sys.path.insert(0, str(ROOT / "code" / "ingest"))

import config
import run_daily as ingest

IST = timezone(timedelta(hours=5, minutes=30))

VARIABLES = ["temperature_2m", "relative_humidity_2m",
             "wind_speed_10m", "wind_direction_10m"]

# (label, host, variable suffix, how many days back it will serve)
ARCHIVES = [
    ("previous-runs (24h lead)",
     "https://previous-runs-api.open-meteo.com/v1/forecast",
     "_previous_day1", None),
    ("historical-forecast (stitched analysis)",
     "https://historical-forecast-api.open-meteo.com/v1/forecast",
     "", None),
    ("forecast endpoint (stitched analysis, 92 day limit)",
     "https://api.open-meteo.com/v1/forecast",
     "", 92),
]

COLUMNS = {"temperature_2m": "temp_mean",
           "relative_humidity_2m": "rh_mean"}


def weather(first, last):
    """Daily means for every day in [first, last].

    Returns (rows, label). `rows` maps an ISO date to the column
    values for that day; `label` names the archive that answered.
    """
    for label, host, suffix, reach in ARCHIVES:
        # Some endpoints only keep a rolling window. Asking for
        # more than they have is a 400, so clamp the request and
        # say plainly which days are being given up.
        start = first
        if reach is not None:
            # IST, not the machine's idea of today: on a UTC runner
            # the boundary would land a day off after 18:30 local.
            earliest = datetime.now(IST).date() - timedelta(days=reach)
            start = max(start, earliest)

        names = [v + suffix for v in VARIABLES]
        url = host + "?" + urllib.parse.urlencode({
            "latitude": config.LAT,
            "longitude": config.LON,
            "hourly": ",".join(names),
            "start_date": start.isoformat(),
            "end_date": last.isoformat(),
            "timezone": "Asia/Kolkata",
        })

        try:
            payload = json.loads(ingest.fetch(url))
        except ingest.SourceError as exc:
            print(f"  {label}: unavailable ({exc})")
            continue

        hourly = payload.get("hourly") or {}
        if not all(n in hourly for n in names) or not hourly.get("time"):
            print(f"  {label}: response missing the requested variables")
            continue

        times = hourly["time"]
        out = {}
        day = start
        while day <= last:
            row = {}
            for variable in VARIABLES[:2]:
                mean = ingest.day_mean(
                    times, hourly[variable + suffix], day)
                if mean is not None:
                    row[COLUMNS[variable]] = round(mean, 2)

            speed, bearing = ingest.wind_day_mean(
                times,
                hourly["wind_speed_10m" + suffix],
                hourly["wind_direction_10m" + suffix],
                day)
            if speed is not None:
                row["wind_speed_mean"] = round(speed, 2)
                row["wind_dir_mean"] = round(bearing, 2)

            if row:
                out[day.isoformat()] = row
            day += timedelta(days=1)

        if out:
            missed = (start - first).days
            note = f", {missed} oldest days out of reach" if missed else ""
            print(f"  {label}: {len(out)} days{note}")
            return out, label

    return {}, "none"


def fires(days):
    """Fire counts for `days`, skipping any FIRMS cannot cover.

    The NRT products only keep a rolling window and answer with an
    empty csv rather than an error outside it, so the helper in the
    ingest module picks a product per date and returns None when
    none of them reaches back that far.
    """
    if not config.FIRMS_MAP_KEY:
        print("  FIRMS_MAP_KEY not set, skipping fire counts")
        return {}

    try:
        sources = ingest.firms_sources()
    except ingest.SourceError as exc:
        print(f"  FIRMS unavailable ({exc})")
        return {}

    out, refused = {}, 0
    for day in days:
        try:
            count = ingest.fire_count(day, sources)
        except ingest.SourceError as exc:
            print(f"  fires {day}: {exc}")
            continue
        if count is None:
            refused += 1
            continue
        out[day.isoformat()] = count

    print(f"  FIRMS: {len(out)} days"
          + (f", {refused} outside the archive window" if refused else ""))
    return out


def report(rows, columns, title):
    print(f"\n{title}")
    for column in columns:
        got = sum(1 for r in rows.values() if r.get(column))
        print(f"    {column:18s} {got:3d}/{len(rows)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="report what would change, write nothing")
    parser.add_argument("--force", action="store_true",
                        help="overwrite existing weather values. Use "
                             "when a better archive comes back online, "
                             "so the whole table has one lead time "
                             "instead of a mixture. Observations, CAMS "
                             "and fire counts are never touched.")
    args = parser.parse_args()

    with open(config.DAILY_CSV, newline="") as f:
        rows = {r["date"]: r for r in csv.DictReader(f)}
    if not rows:
        print("daily.csv is empty; run scripts/bootstrap.py first")
        return 1

    tracked = ["temp_mean", "rh_mean", "wind_speed_mean",
               "wind_dir_mean", "fire_count"]
    report(rows, tracked, f"Before ({len(rows)} rows):")

    days = sorted(date.fromisoformat(d) for d in rows)
    first, last = days[0], days[-1]

    print(f"\nFetching weather for {first} .. {last}")
    wx, source = weather(first, last)

    wanted = [d for d in days
              if not rows[d.isoformat()].get("fire_count")]
    print(f"\nFetching fire counts for {len(wanted)} days without one")
    fire = fires(wanted)

    filled = 0
    for key, row in rows.items():
        for column, value in (wx.get(key) or {}).items():
            # Blanks always get filled. Existing values only when
            # asked, because a half-replaced table would carry two
            # different lead times and nothing would say which row
            # had which.
            if args.force or not row.get(column):
                row[column] = value
                filled += 1
        if not row.get("fire_count") and key in fire:
            row["fire_count"] = fire[key]
            filled += 1

    report(rows, tracked, f"After ({filled} cells filled):")

    if args.dry_run:
        print("\ndry run, nothing written")
        return 0

    stamp = datetime.now(IST).isoformat(timespec="seconds")
    with open(config.DAILY_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=config.COLUMNS)
        writer.writeheader()
        for key in sorted(rows):
            row = dict(rows[key])
            if not row.get("ingested_at"):
                row["ingested_at"] = stamp
            writer.writerow({c: row.get(c, "") for c in config.COLUMNS})

    print(f"\nwrote {config.DAILY_CSV}")
    print(f"weather source: {source}")
    print("Record that source in the journal -- it decides whether the "
          "meteorology is a true forecast or a stand-in.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
