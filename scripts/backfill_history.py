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

--force only ever touches backfilled rows. Rows the daily job
wrote carry the weather forecast it actually saw the day before,
which is the real thing every archive here is standing in for,
and no archive is a better source for them than that.

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

Each day is taken from the best archive that has it, and the next
one down is only asked for the days still missing. Which archive
supplied how many days is printed and goes in the journal, because
it changes how the numbers should be read.
"""

import argparse
import csv
import json
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
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

WEATHER_COLUMNS = ["temp_mean", "rh_mean", "wind_speed_mean",
                   "wind_dir_mean"]

# No request asks for more than this many days. Open-Meteo does not
# publish a limit, but a year and a half of hourly values for four
# variables in one URL is the kind of request that times out on a
# slow morning, and retrying a small piece is cheaper than retrying
# the whole range.
CHUNK_DAYS = 120


def day_rows(times, hourly, suffix, days):
    """Weather columns for each of `days` that has all four values.

    A day missing any one of them is left out entirely rather than
    filled in part, so no row ends up with temperature from one
    archive and wind from another.
    """
    index = defaultdict(list)
    for i, t in enumerate(times):
        index[t[:10]].append(i)

    out = {}
    for day in days:
        picked = index.get(day.isoformat())
        if not picked:
            continue
        sub = {name: [hourly[name + suffix][i] for i in picked]
               for name in VARIABLES}
        sub_times = [times[i] for i in picked]
        row = {}
        for variable in VARIABLES[:2]:
            mean = ingest.day_mean(sub_times, sub[variable], day)
            if mean is not None:
                row[COLUMNS[variable]] = round(mean, 2)
        speed, bearing = ingest.wind_day_mean(
            sub_times, sub["wind_speed_10m"],
            sub["wind_direction_10m"], day)
        if speed is not None:
            row["wind_speed_mean"] = round(speed, 2)
            row["wind_dir_mean"] = round(bearing, 2)
        if all(c in row for c in WEATHER_COLUMNS):
            out[day.isoformat()] = row
    return out


def weather(days):
    """Daily means for as many of `days` as the archives cover.

    Returns (rows, sources). `rows` maps an ISO date to the column
    values for that day; `sources` maps each archive's label to the
    number of days it supplied.

    The first version stopped at the first archive that answered at
    all. An archive with a shorter reach than the table then left
    the oldest rows blank without trying anything else, which is
    the wrong way round: the better archive should get every day it
    has, and the fallback only the ones it does not.
    """
    out, sources = {}, {}
    today = datetime.now(IST).date()
    for label, host, suffix, reach in ARCHIVES:
        wanted = [d for d in days if d.isoformat() not in out]
        if reach is not None:
            # IST, not the machine's idea of today: on a UTC runner
            # the boundary would land a day off after 18:30 local.
            earliest = today - timedelta(days=reach)
            wanted = [d for d in wanted if d >= earliest]
        if not wanted:
            continue

        names = [v + suffix for v in VARIABLES]
        got = 0
        for start, end in chunks(wanted[0], wanted[-1], CHUNK_DAYS):
            inside = [d for d in wanted if start <= d <= end]
            if not inside:
                continue
            url = host + "?" + urllib.parse.urlencode({
                "latitude": config.LAT,
                "longitude": config.LON,
                "hourly": ",".join(names),
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "timezone": "Asia/Kolkata",
            })
            try:
                payload = json.loads(ingest.fetch(url))
            except ingest.SourceError as exc:
                print(f"  {label} {start} .. {end}: unavailable ({exc})")
                continue

            hourly = payload.get("hourly") or {}
            if not all(n in hourly for n in names) or not hourly.get("time"):
                print(f"  {label} {start} .. {end}: "
                      f"response missing the requested variables")
                continue

            found = day_rows(hourly["time"], hourly, suffix, inside)
            out.update(found)
            got += len(found)

        print(f"  {label}: {got} days")
        if got:
            sources[label] = got

    left = len([d for d in days if d.isoformat() not in out])
    if left:
        print(f"  {left} days not covered by any archive")
    return out, sources


def chunks(first, last, size):
    """[first, last] cut into consecutive (start, end) pieces."""
    start = first
    while start <= last:
        end = min(start + timedelta(days=size - 1), last)
        yield start, end
        start = end + timedelta(days=1)


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
    for i, day in enumerate(days, 1):
        if i % 50 == 0:
            print(f"  fires: {i}/{len(days)}")
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


def apply(rows, wx, fire, force=False):
    """Write fetched weather and fires into `rows`. Returns cells filled.

    Blanks always get filled. Existing weather is replaced only with
    `force`, and only on backfilled rows (no cams_issue_date): a
    live row's weather is the forecast that was really issued, and
    an archive is only ever an imitation of that. Fire counts are
    never replaced.
    """
    filled = 0
    for key, row in rows.items():
        live = bool(row.get("cams_issue_date"))
        for column, value in (wx.get(key) or {}).items():
            replace = not row.get(column) or (force and not live)
            if replace and str(row.get(column, "")) != str(value):
                row[column] = value
                filled += 1
        if not row.get("fire_count") and key in fire:
            row["fire_count"] = fire[key]
            filled += 1
    return filled


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="report what would change, write nothing")
    parser.add_argument("--force", action="store_true",
                        help="refetch weather for every backfilled row, "
                             "so the whole history comes from the best "
                             "archive instead of a mixture. Live rows, "
                             "observations, CAMS and fire counts are "
                             "never touched.")
    args = parser.parse_args()

    with open(config.DAILY_CSV, newline="") as f:
        rows = {r["date"]: r for r in csv.DictReader(f)}
    if not rows:
        print("daily.csv is empty; run scripts/bootstrap.py first")
        return 1

    tracked = WEATHER_COLUMNS + ["fire_count"]
    report(rows, tracked, f"Before ({len(rows)} rows):")

    # Only days that happened. Tomorrow's row already carries the
    # live forecast, and an archive cannot know a day in the future.
    today = datetime.now(IST).date()
    if args.force:
        need = [k for k, r in rows.items() if not r.get("cams_issue_date")]
    else:
        need = [k for k, r in rows.items()
                if any(not r.get(c) for c in WEATHER_COLUMNS)]
    days = sorted(date.fromisoformat(k) for k in need)
    days = [d for d in days if d < today]

    wx, sources = {}, {}
    if days:
        print(f"\nFetching weather for {len(days)} days, "
              f"{days[0]} .. {days[-1]}")
        wx, sources = weather(days)

    wanted = sorted(date.fromisoformat(k) for k, r in rows.items()
                    if not r.get("fire_count")
                    and date.fromisoformat(k) < today)
    print(f"\nFetching fire counts for {len(wanted)} days without one")
    fire = fires(wanted)

    filled = apply(rows, wx, fire, force=args.force)
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
    print("weather sources:")
    for label, count in sources.items():
        print(f"    {label:50s} {count:4d} days")
    print("Record those in the journal -- they decide whether the "
          "meteorology is a true forecast or a stand-in.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
