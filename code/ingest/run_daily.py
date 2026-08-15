"""Daily ingest. Fills in yesterday's observation, adds tomorrow's
forecast. Run by .github/workflows/ingest.yml each morning."""

import csv
import io
import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

IST = timezone(timedelta(hours=5, minutes=30))


def fetch(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read().decode("utf-8", errors="replace")


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


def fire_count(day):
    """Fire detections in the bbox for one date."""
    # NRT products cover only a recent window and return an empty
    # csv, not an error, outside it. Pick the source by date.
    avail = fetch("https://firms.modaps.eosdis.nasa.gov/api/"
                  f"data_availability/csv/{config.FIRMS_MAP_KEY}/all")
    source = None
    for r in csv.DictReader(io.StringIO(avail)):
        name = r.get("data_id") or r.get("source") or ""
        lo, hi = r.get("min_date", ""), r.get("max_date", "")
        if "VIIRS" in name.upper() and lo and hi \
                and lo <= day.isoformat() <= hi:
            source = name
            break
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
    yesterday = today - timedelta(days=1)
    tomorrow = today + timedelta(days=1)
    rows = load()
    stamp = datetime.now(IST).isoformat(timespec="seconds")
    changed = 0

    # yesterday: fill in what is only knowable now
    row = rows.get(yesterday.isoformat(), blank(yesterday))
    if not row.get("obs_pm25"):
        mean, hours = observed(yesterday)
        if mean is not None:
            row["obs_pm25"] = round(mean, 2)
            row["obs_hours"] = hours
            changed += 1
            print(f"obs {yesterday}: {mean:.1f} ug/m3 ({hours}h)")
        else:
            print(f"obs {yesterday}: no data")
    if not row.get("fire_count"):
        n = fire_count(yesterday)
        if n is not None:
            row["fire_count"] = n
            changed += 1
            print(f"fires {yesterday}: {n}")
    row["ingested_at"] = stamp
    rows[yesterday.isoformat()] = row

    # tomorrow: the forecast issued today, with its issue date
    row = rows.get(tomorrow.isoformat(), blank(tomorrow))
    if not row.get("cams_pm25"):
        f = forecast(tomorrow)
        if f["cams_pm25"] is not None:
            row.update({k: (round(v, 2) if v is not None else "")
                        for k, v in f.items()})
            row["cams_issue_date"] = today.isoformat()
            changed += 1
            print(f"forecast {tomorrow}: {f['cams_pm25']:.1f} ug/m3 "
                  f"(issued {today})")
    row["ingested_at"] = stamp
    rows[tomorrow.isoformat()] = row

    save(rows)
    print(f"{len(rows)} rows, {changed} field group(s) updated")
    if changed == 0:
        print("WARNING: nothing new was written")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
