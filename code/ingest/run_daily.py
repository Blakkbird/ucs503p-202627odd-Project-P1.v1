"""Daily ingest. Backfills recent observations, adds tomorrow's
forecast. Run by .github/workflows/ingest.yml each morning."""

import csv
import io
import json
import math
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

IST = timezone(timedelta(hours=5, minutes=30))

# Observations arrive with a lag of a day or two, so a job that
# only ever looks at yesterday leaves permanent holes. Re-check a
# rolling window instead; already-filled fields are skipped.
#
# The window was 10, which turned out to be a trap. When the
# observation feed broke on 15 August the hole grew a day at a
# time until it was wider than the window, and after that the
# window slid past it: every run looked only at days that were
# already hopeless, so the job could never have recovered even
# once the feed came back. A window has to be wider than the
# outage it is meant to survive. Filled cells cost nothing to
# skip, so the only price of a generous window is a handful of
# requests on the days when there is genuinely something to fetch.
BACKFILL_DAYS = 30

RETRIES = 3
TIMEOUT = 45

# CI runners sometimes have no usable IPv6 route, and urllib tries
# the AAAA record first, failing with "Network is unreachable"
# instead of falling back. Restrict resolution to IPv4.
_getaddrinfo = socket.getaddrinfo


def _ipv4_only(*args, **kwargs):
    return [r for r in _getaddrinfo(*args, **kwargs)
            if r[0] == socket.AF_INET]


socket.getaddrinfo = _ipv4_only


class SourceError(Exception):
    """A data source could not be reached or returned nonsense."""


def fetch(url, headers=None):
    """GET with retries. Raises SourceError once attempts run out."""
    last = None
    for attempt in range(1, RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers=headers or {})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return r.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            # 4xx will not fix itself; only retry server-side faults
            if e.code < 500:
                raise SourceError(f"HTTP {e.code} for {url[:60]}") from e
            last = e
        except (TimeoutError, urllib.error.URLError, OSError) as e:
            last = e
        if attempt < RETRIES:
            wait = 2 ** attempt
            print(f"  retry {attempt}/{RETRIES - 1} in {wait}s ({last})")
            time.sleep(wait)
    raise SourceError(f"unreachable after {RETRIES} tries: {last}")


def parse_days(payload, start, end):
    """{iso date: (daily mean, hours behind it)} from a /days body.

    Split out from the request so it can be tested without a
    network, which the thing it replaces could not be. v3 ignores
    query parameters it does not recognise and answers with some
    other window rather than an error, so the dates that come back
    are checked again here instead of being trusted.

    `hours` is None when the payload carries no coverage count.
    That is recorded rather than guessed at: a mean over four
    hours and a mean over twenty-four are both means, and the
    difference belongs in the data, not in a silent assumption.
    """
    out = {}
    for row in payload.get("results", []):
        day = ((row.get("period") or {}).get("datetimeFrom")
               or {}).get("local", "")[:10]
        val = row.get("value")
        if not day or val is None:
            continue
        if not (start.isoformat() <= day <= end.isoformat()):
            continue
        out[day] = (float(val), (row.get("coverage") or {})
                    .get("observedCount"))
    return out


def observed_window(start, end):
    """Daily means for a date range, in one request.

    The /days endpoint, deliberately, not /hours. The daily job
    asked /hours for a single day at a time and got an empty
    result set back every morning for three weeks while the sensor
    was publishing normally the whole time -- scripts/bootstrap.py
    and scripts/check_sensor.py both read the same sensor over
    /days without trouble. Whatever /hours wanted, it was not what
    was being sent, and it said so by returning nothing at all,
    which the caller could not tell apart from a quiet day.

    Taking the range in one request rather than one request per
    day is the other half of it: a thirty-day backfill costs one
    call, and a bad morning is one failure in the log instead of
    thirty.
    """
    params = {
        "date_from": start.isoformat(),
        "date_to": end.isoformat(),
        "limit": 1000,
    }
    url = (f"https://api.openaq.org/v3/sensors/"
           f"{config.OPENAQ_PM25_SENSOR_ID}/days?"
           + urllib.parse.urlencode(params))
    data = json.loads(fetch(url, {"X-API-Key": config.OPENAQ_KEY}))
    return parse_days(data, start, end)


def day_mean(times, values, day):
    """Mean of the hourly values that fall on `day`."""
    picked = [v for t, v in zip(times, values)
              if t[:10] == day.isoformat() and v is not None]
    return sum(picked) / len(picked) if picked else None


def wind_day_mean(times, speeds, bearings, day):
    """Daily mean wind as (speed, bearing).

    Averaging bearings arithmetically is wrong: 350 deg and 10 deg
    are twenty degrees apart but average to 180, i.e. exactly
    backwards. Resolve each hour into components, average those,
    and convert back. Speed is taken as the mean of the hourly
    speeds rather than the length of the mean vector, so that a day
    of swirling wind still reads as windy.
    """
    hours = [(s, b) for t, s, b in zip(times, speeds, bearings)
             if t[:10] == day.isoformat() and s is not None
             and b is not None]
    if not hours:
        return None, None

    u = sum(-s * math.sin(math.radians(b)) for s, b in hours) / len(hours)
    v = sum(-s * math.cos(math.radians(b)) for s, b in hours) / len(hours)
    speed = sum(s for s, _ in hours) / len(hours)
    bearing = (math.degrees(math.atan2(-u, -v))) % 360
    return speed, bearing


def forecast(target_day):
    """CAMS pm2.5 and weather for target_day, as issued today."""
    aq = json.loads(fetch(
        "https://air-quality-api.open-meteo.com/v1/air-quality?"
        + urllib.parse.urlencode({
            "latitude": config.LAT, "longitude": config.LON,
            "hourly": "pm2_5", "forecast_days": 3,
            "timezone": "Asia/Kolkata", "domains": "cams_global"})))

    wx = json.loads(fetch(
        "https://api.open-meteo.com/v1/forecast?"
        + urllib.parse.urlencode({
            "latitude": config.LAT, "longitude": config.LON,
            "hourly": ("temperature_2m,relative_humidity_2m,"
                       "wind_speed_10m,wind_direction_10m"),
            "forecast_days": 3, "timezone": "Asia/Kolkata"})))

    t_aq = aq["hourly"]["time"]
    t_wx = wx["hourly"]["time"]
    speed, bearing = wind_day_mean(
        t_wx, wx["hourly"]["wind_speed_10m"],
        wx["hourly"]["wind_direction_10m"], target_day)

    return {
        "cams_pm25": day_mean(t_aq, aq["hourly"]["pm2_5"], target_day),
        "temp_mean": day_mean(
            t_wx, wx["hourly"]["temperature_2m"], target_day),
        "rh_mean": day_mean(
            t_wx, wx["hourly"]["relative_humidity_2m"], target_day),
        "wind_speed_mean": speed,
        "wind_dir_mean": bearing,
    }


def firms_sources():
    """Available FIRMS products with their date coverage."""
    # NRT products cover only a recent window and return an empty
    # csv, not an error, outside it. Pick the source by date.
    text = fetch("https://firms.modaps.eosdis.nasa.gov/api/"
                 f"data_availability/csv/{config.FIRMS_MAP_KEY}/all")
    out = []
    for r in csv.DictReader(io.StringIO(text)):
        name = r.get("data_id") or r.get("source") or ""
        lo, hi = r.get("min_date", ""), r.get("max_date", "")
        if "VIIRS" in name.upper() and lo and hi:
            out.append((name, lo, hi))
    return out


def fire_count(day, sources):
    """Fire detections in the bbox for one date."""
    source = next((n for n, lo, hi in sources
                   if lo <= day.isoformat() <= hi), None)
    if source is None:
        return None
    text = fetch("https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
                 f"{config.FIRMS_MAP_KEY}/{source}/"
                 f"{config.FIRMS_BBOX}/1/{day.isoformat()}")
    if text.strip().lower().startswith(("invalid", "error")):
        return None
    return len(list(csv.DictReader(io.StringIO(text))))


def load():
    if not config.DAILY_CSV.exists():
        return {}
    with open(config.DAILY_CSV, newline="") as f:
        return {r["date"]: r for r in csv.DictReader(f)}


def save(rows):
    config.DATA.mkdir(exist_ok=True)
    with open(config.DAILY_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=config.COLUMNS)
        w.writeheader()
        for d in sorted(rows):
            w.writerow({c: rows[d].get(c, "") for c in config.COLUMNS})


def blank(day):
    return {c: "" for c in config.COLUMNS} | {"date": day.isoformat()}


def obs_staleness(rows, today):
    """Days between `today` and the freshest observation on record.

    None when there is no observation at all.

    This exists because a dead observation feed does not look like
    a failure from inside the backfill loop. Each day's fetch
    raises, the exception is caught so one bad source cannot take
    down the rest, the forecast still lands, and the job exits
    green. It did that every morning for a fortnight while the
    training data sat frozen. The staleness of the record is the
    thing that actually went wrong, so that is what to check.
    """
    seen = [d for d, r in rows.items() if r.get("obs_pm25")]
    if not seen:
        return None
    return (today - date.fromisoformat(max(seen))).days


def main():
    today = datetime.now(IST).date()
    tomorrow = today + timedelta(days=1)
    rows = load()
    stamp = datetime.now(IST).isoformat(timespec="seconds")
    changed = 0
    sources = None
    failures = []

    # Backfill any gap in the recent window, not just yesterday.
    # A failure on one source or one day must not abort the rest:
    # partial data written today is better than nothing, and the
    # window means we retry tomorrow anyway.
    # One request for the whole window, before the loop. See
    # observed_window: the old code asked per day and a failure
    # was therefore also per day, which made a systematic outage
    # look like a run of unrelated quiet ones.
    obs_window = {}
    try:
        obs_window = observed_window(
            today - timedelta(days=BACKFILL_DAYS), today)
    except SourceError as e:
        failures.append(f"obs window: {e}")

    for n in range(BACKFILL_DAYS, 0, -1):
        day = today - timedelta(days=n)
        row = rows.get(day.isoformat(), blank(day))
        touched = False

        if not row.get("obs_pm25"):
            mean, hours = obs_window.get(day.isoformat(), (None, None))
            if mean is not None:
                row["obs_pm25"] = round(mean, 2)
                row["obs_hours"] = "" if hours is None else hours
                touched = True
                print(f"obs   {day}: {mean:.1f} ug/m3"
                      + ("" if hours is None else f" ({hours}h)"))

        if not row.get("fire_count"):
            try:
                if sources is None:
                    sources = firms_sources()
                n_fires = fire_count(day, sources)
                if n_fires is not None:
                    row["fire_count"] = n_fires
                    touched = True
                    print(f"fires {day}: {n_fires}")
            except SourceError as e:
                failures.append(f"fires {day}: {e}")
                sources = sources or []   # do not retry all ten days

        if touched:
            row["ingested_at"] = stamp
            rows[day.isoformat()] = row
            changed += 1

    # tomorrow: the forecast issued today, with its issue date
    row = rows.get(tomorrow.isoformat(), blank(tomorrow))
    if not row.get("cams_pm25"):
        try:
            f = forecast(tomorrow)
            if f["cams_pm25"] is not None:
                row.update({k: (round(v, 2) if v is not None else "")
                            for k, v in f.items()})
                row["cams_issue_date"] = today.isoformat()
                row["ingested_at"] = stamp
                rows[tomorrow.isoformat()] = row
                changed += 1
                print(f"fcst  {tomorrow}: {f['cams_pm25']:.1f} ug/m3 "
                      f"(issued {today})")
        except SourceError as e:
            failures.append(f"forecast {tomorrow}: {e}")

    save(rows)

    still_missing = [d for d in sorted(rows)
                     if d < today.isoformat() and not rows[d]["obs_pm25"]]
    print(f"\n{len(rows)} rows, {changed} updated, "
          f"{len(still_missing)} past days still without an observation")

    if failures:
        print(f"{len(failures)} source failure(s):")
        for f_msg in failures[:5]:
            print(f"  {f_msg}")

    # A second run on the same day legitimately has nothing to do,
    # so "changed == 0" is not a failure. Both checks below run
    # after save(), so a red run still leaves today's data on disk
    # for the workflow to commit -- the point is to raise a hand,
    # not to throw away the rows we did manage to get.
    ok = True

    if not rows.get(tomorrow.isoformat(), {}).get("cams_pm25"):
        print(f"ERROR: no forecast for {tomorrow}")
        ok = False

    stale = obs_staleness(rows, today)
    if stale is None:
        print("ERROR: not one observation in the whole record")
        ok = False
    elif stale > config.OBS_STALENESS_LIMIT_DAYS:
        print(f"ERROR: freshest observation is {stale} days old, "
              f"limit is {config.OBS_STALENESS_LIMIT_DAYS}. "
              "The observation feed is not being written -- check "
              "the OPENAQ_KEY secret and the obs lines above.")
        ok = False

    if changed == 0:
        print("already up to date")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
