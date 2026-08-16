"""Daily ingest. Backfills recent observations, adds tomorrow's
forecast. Run by .github/workflows/ingest.yml each morning."""

import csv
import io
import json
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

IST = timezone(timedelta(hours=5, minutes=30))

# Observations arrive with a lag of a day or two, so a job that
# only ever looks at yesterday leaves permanent holes. Re-check a
# rolling window instead; already-filled fields are skipped.
BACKFILL_DAYS = 10

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


def observed(day):
    """Daily mean and hour count for one date."""
    # v3 wants date_from/date_to. A wrong name is dropped silently
    # and the oldest rows come back instead, so filter again below.
    params = {
        "date_from": day.isoformat(),
        "date_to": (day + timedelta(days=1)).isoformat(),
        "limit": 200,
    }
    url = (f"https://api.openaq.org/v3/sensors/"
           f"{config.OPENAQ_PM25_SENSOR_ID}/hours?"
           + urllib.parse.urlencode(params))
    data = json.loads(fetch(url, {"X-API-Key": config.OPENAQ_KEY}))

    vals = []
    for row in data.get("results", []):
        t = ((row.get("period") or {}).get("datetimeFrom")
             or {}).get("local", "")
        if t[:10] == day.isoformat() and row.get("value") is not None:
            vals.append(float(row["value"]))
    if not vals:
        return None, 0
    return sum(vals) / len(vals), len(vals)


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

    def day_mean(times, values, day):
        picked = [v for t, v in zip(times, values)
                  if t[:10] == day.isoformat() and v is not None]
        return sum(picked) / len(picked) if picked else None

    t_aq = aq["hourly"]["time"]
    t_wx = wx["hourly"]["time"]
    return {
        "cams_pm25": day_mean(t_aq, aq["hourly"]["pm2_5"], target_day),
        "temp_mean": day_mean(
            t_wx, wx["hourly"]["temperature_2m"], target_day),
        "rh_mean": day_mean(
            t_wx, wx["hourly"]["relative_humidity_2m"], target_day),
        "wind_speed_mean": day_mean(
            t_wx, wx["hourly"]["wind_speed_10m"], target_day),
        "wind_dir_mean": day_mean(
            t_wx, wx["hourly"]["wind_direction_10m"], target_day),
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
    for n in range(BACKFILL_DAYS, 0, -1):
        day = today - timedelta(days=n)
        row = rows.get(day.isoformat(), blank(day))
        touched = False

        if not row.get("obs_pm25"):
            try:
                mean, hours = observed(day)
                if mean is not None:
                    row["obs_pm25"] = round(mean, 2)
                    row["obs_hours"] = hours
                    touched = True
                    print(f"obs   {day}: {mean:.1f} ug/m3 ({hours}h)")
            except SourceError as e:
                failures.append(f"obs {day}: {e}")

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
    # so "changed == 0" is not a failure. Fail only when the thing
    # this job exists to produce is missing.
    if not rows.get(tomorrow.isoformat(), {}).get("cams_pm25"):
        print(f"ERROR: no forecast for {tomorrow}")
        return 1
    if changed == 0:
        print("already up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
