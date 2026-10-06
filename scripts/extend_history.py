"""Extend daily.csv back to the start of the live sensor.

scripts/bootstrap.py seeded the table with 92 days, on the belief
that this was as far back as Open-Meteo kept CAMS. It was not. 92
is the ceiling on `past_days`; an explicit start_date and end_date
reach the global CAMS archive back to August 2022. The live sensor
at Model Town has reported since February 2025, so the whole 2025
burning season was available the entire time, and the model was
trained on summer and monsoon alone.

This adds the days that are missing, with the observation and CAMS
for each, and fills cells that are blank. A value already in the
table is left alone, with the same two exceptions the daily job
makes:

  * a thin observation is replaced when the feed now has more
    hours behind the same day (run_daily.merge_obs);
  * a blank hour count is filled in. bootstrap.py never recorded
    one, so its rows were taken on trust, and once the count is
    known the 16-hour rule applies to them like everything else.
    It is only copied when the fetched mean matches the stored
    one, so it is known to describe the same reading.

    python scripts/extend_history.py --dry-run
    python scripts/extend_history.py
    python scripts/backfill_history.py --force

The second script fills weather and fire counts for the new rows.
Rows added here have no cams_issue_date, like every other row that
came from an archive: they are training history, never part of the
live record.
"""

import argparse
import json
import sys
import urllib.parse
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))
sys.path.insert(0, str(ROOT / "code" / "ingest"))

import config
import run_daily as ingest

IST = timezone(timedelta(hours=5, minutes=30))

# First month the live sensor (12235142) has data for. Asking for
# earlier is harmless, it just comes back empty.
SENSOR_START = date(2025, 2, 1)

# OpenAQ caps a page at 1000 rows; half a year is well inside it.
OBS_CHUNK_DAYS = 180

# CAMS comes back hourly, so a quarter is about 2000 values. Small
# enough that one slow response does not cost the whole run.
CAMS_CHUNK_DAYS = 90

# A day of CAMS with fewer hours than this is a fetch that broke
# partway, not a forecast, and is left blank.
MIN_CAMS_HOURS = 20


def chunks(first, last, size):
    """[first, last] cut into consecutive (start, end) pieces."""
    start = first
    while start <= last:
        end = min(start + timedelta(days=size - 1), last)
        yield start, end
        start = end + timedelta(days=1)


def observations(first, last):
    """{iso date: (mean, hours)} from the OpenAQ daily endpoint."""
    out = {}
    for start, end in chunks(first, last, OBS_CHUNK_DAYS):
        try:
            got = ingest.observed_window(start, end)
        except ingest.SourceError as exc:
            print(f"  obs {start} .. {end}: {exc}")
            continue
        print(f"  obs {start} .. {end}: {len(got)} days")
        out.update(got)
    return out


def cams_means(times, values):
    """Daily means from an hourly series, skipping broken days."""
    buckets = defaultdict(list)
    for t, v in zip(times, values):
        if v is not None:
            buckets[t[:10]].append(v)
    return {d: sum(v) / len(v) for d, v in buckets.items()
            if len(v) >= MIN_CAMS_HOURS}


def cams(first, last):
    """{iso date: daily mean CAMS pm2.5} from the archive.

    Same request as the daily job apart from the date range, so
    the two are the same quantity. The archive is stitched from
    the opening hours of successive runs rather than read at a
    fixed lead, which makes it a little closer to what happened
    than a true day-ahead forecast. docs/data.md has the caveat.
    """
    out = {}
    for start, end in chunks(first, last, CAMS_CHUNK_DAYS):
        url = ("https://air-quality-api.open-meteo.com/v1/air-quality?"
               + urllib.parse.urlencode({
                   "latitude": config.LAT,
                   "longitude": config.LON,
                   "hourly": "pm2_5",
                   "start_date": start.isoformat(),
                   "end_date": end.isoformat(),
                   "timezone": "Asia/Kolkata",
                   "domains": "cams_global",
               }))
        try:
            payload = json.loads(ingest.fetch(url))
        except ingest.SourceError as exc:
            print(f"  cams {start} .. {end}: {exc}")
            continue
        hourly = payload.get("hourly") or {}
        got = cams_means(hourly.get("time", []), hourly.get("pm2_5", []))
        print(f"  cams {start} .. {end}: {len(got)} days")
        out.update(got)
    return out


def merge(rows, obs, cams_by_day, stamp):
    """Fold fetched values into `rows`. Returns counts of each change.

    A missing day gets a row only if it has an observation; a CAMS
    value with nothing to check it against adds nothing.
    """
    counts = {"added": 0, "obs_filled": 0, "hours_filled": 0,
              "cams_filled": 0}
    for day, (mean, hours) in obs.items():
        if day not in rows:
            row = ingest.blank(date.fromisoformat(day))
            row["obs_pm25"] = round(mean, 2)
            row["obs_hours"] = "" if hours is None else hours
            row["ingested_at"] = stamp
            rows[day] = row
            counts["added"] += 1
            continue

        row = rows[day]
        if ingest.merge_obs(row, mean, hours):
            row["ingested_at"] = stamp
            counts["obs_filled"] += 1
            continue

        stored = num(row.get("obs_pm25"))
        if (hours is not None and not row.get("obs_hours")
                and stored is not None and abs(stored - mean) < 0.05):
            row["obs_hours"] = hours
            counts["hours_filled"] += 1

    for day, value in cams_by_day.items():
        row = rows.get(day)
        if row is not None and not row.get("cams_pm25"):
            row["cams_pm25"] = round(value, 2)
            counts["cams_filled"] += 1
    return counts


def num(cell):
    """CSV cell to float, or None when it is blank or junk."""
    try:
        return float(cell)
    except (TypeError, ValueError):
        return None


def summary(rows, title):
    """What the table holds, with burning-season days counted apart."""
    with_obs = [d for d, r in rows.items() if r.get("obs_pm25")]
    burning = [d for d in with_obs
               if date.fromisoformat(d).month in config.BURNING_MONTHS]
    thin = [d for d in with_obs
            if (num(rows[d].get("obs_hours")) or 99)
            < config.MIN_OBS_HOURS]
    first = min(rows) if rows else "-"
    print(f"\n{title}")
    print(f"    rows                {len(rows):4d}   from {first}")
    print(f"    with observation    {len(with_obs):4d}")
    print(f"    burning season      {len(burning):4d}")
    print(f"    thin (< {config.MIN_OBS_HOURS}h)         {len(thin):4d}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=date.fromisoformat,
                        default=SENSOR_START,
                        help="first day to fetch (default %(default)s)")
    parser.add_argument("--dry-run", action="store_true",
                        help="report what would change, write nothing")
    args = parser.parse_args()

    rows = ingest.load()
    if not rows:
        print("daily.csv is empty; nothing to extend")
        return 1
    summary(rows, "Before:")

    # Up to yesterday rather than up to the first existing row, so
    # the rows bootstrap.py wrote get their hour counts too, and
    # any old gap the daily job's 30-day window can no longer
    # reach gets a second chance.
    last = datetime.now(IST).date() - timedelta(days=1)
    print(f"\nFetching {args.start} .. {last}")
    obs = observations(args.start, last)
    cams_by_day = cams(args.start, last)

    stamp = datetime.now(IST).isoformat(timespec="seconds")
    counts = merge(rows, obs, cams_by_day, stamp)
    summary(rows, "After:")
    print(f"\n    {counts['added']} rows added, "
          f"{counts['obs_filled']} observations filled or refreshed, "
          f"{counts['hours_filled']} hour counts filled, "
          f"{counts['cams_filled']} CAMS cells filled")

    no_cams = [d for d, r in rows.items()
               if r.get("obs_pm25") and not r.get("cams_pm25")]
    if no_cams:
        print(f"    {len(no_cams)} observed days still have no CAMS "
              f"value and will not be fitted")

    if args.dry_run:
        print("\ndry run, nothing written")
        return 0

    ingest.save(rows)
    print(f"\nwrote {config.DAILY_CSV}")
    print("next: python scripts/backfill_history.py --force")
    return 0


if __name__ == "__main__":
    sys.exit(main())
