"""One-time: pull history and print the baseline errors used
in the proposal. No model involved, just arithmetic.

Rows written here have no cams_issue_date, so they are valid
for baselines but not for training."""

import csv
import json
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "code"))
import config

IST = timezone(timedelta(hours=5, minutes=30))

PAST_DAYS = 92  # the CAMS archive window Open-Meteo exposes


def fetch(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read().decode("utf-8", errors="replace")


# --- observations ---------------------------------------------

def observed_daily():
    """Daily mean pm2.5 per date, from OpenAQ.

    v3 takes date_from/date_to and ignores unknown params, so the
    window is enforced client-side too.
    """
    if not config.OPENAQ_PM25_SENSOR_ID:
        print("OPENAQ_PM25_SENSOR_ID not set in config.py")
        print("Run scripts/find_station.py then check_sensor.py.")
        return {}

    end = datetime.now(IST).date()
    start = end - timedelta(days=PAST_DAYS + 5)

    results, page = [], 1
    while page <= 5:
        params = {
            "date_from": start.isoformat(),
            "date_to": end.isoformat(),
            "limit": 1000,
            "page": page,
        }
        url = (f"https://api.openaq.org/v3/sensors/"
               f"{config.OPENAQ_PM25_SENSOR_ID}/days?"
               + urllib.parse.urlencode(params))
        data = json.loads(fetch(url, {"X-API-Key": config.OPENAQ_KEY}))
        got = data.get("results", [])
        if not got:
            break
        results.extend(got)
        if len(got) < 1000:
            break
        page += 1

    out, dropped = {}, 0
    for row in results:
        day = ((row.get("period") or {}).get("datetimeFrom")
               or {}).get("local", "")[:10]
        val = row.get("value")
        if not day or val is None:
            continue
        if not (start.isoformat() <= day <= end.isoformat()):
            dropped += 1
            continue
        out[day] = float(val)

    if dropped:
        print(f"  dropped {dropped} rows outside the requested window")
    return out


# --- forecast -------------------------------------------------

def cams_daily():
    """Daily mean of the CAMS pm2.5 forecast, plus weather."""
    params = {
        "latitude": config.LAT,
        "longitude": config.LON,
        "hourly": "pm2_5",
        "past_days": PAST_DAYS,
        "forecast_days": 1,
        "timezone": "Asia/Kolkata",
        "domains": "cams_global",
    }
    url = ("https://air-quality-api.open-meteo.com/v1/air-quality?"
           + urllib.parse.urlencode(params))
    data = json.loads(fetch(url))

    buckets = defaultdict(list)
    for t, v in zip(data["hourly"]["time"], data["hourly"]["pm2_5"]):
        if v is not None:
            buckets[t[:10]].append(v)
    return {d: sum(v) / len(v) for d, v in buckets.items()}


# --- baselines ------------------------------------------------

def mae(pairs):
    return sum(abs(a - b) for a, b in pairs) / len(pairs) if pairs else None


def main():
    print("Pulling observations ...")
    obs = observed_daily()
    print(f"  {len(obs)} days of observed daily means")

    print("Pulling CAMS forecast archive ...")
    cams = cams_daily()
    print(f"  {len(cams)} days of CAMS daily means")

    days = sorted(set(obs) & set(cams))
    print(f"  {len(days)} overlapping days\n")

    if len(days) < 10:
        print("Not enough overlap to compute baselines.")
        return 1

    # persistence: today's observation predicts tomorrow's
    pers_pairs = []
    for i in range(1, len(days)):
        prev, cur = days[i - 1], days[i]
        if (date.fromisoformat(cur) - date.fromisoformat(prev)).days == 1:
            pers_pairs.append((obs[cur], obs[prev]))

    # climatology: the mean of all observed days
    obs_mean = sum(obs[d] for d in days) / len(days)
    clim_pairs = [(obs[d], obs_mean) for d in days]

    # raw cams: the uncorrected global forecast
    cams_pairs = [(obs[d], cams[d]) for d in days]

    print("=" * 52)
    print("  BASELINES  (put these in the proposal table)")
    print("=" * 52)
    print(f"  days of overlapping record : {len(days)}")
    print(f"  observed mean PM2.5        : {obs_mean:6.1f} ug/m3")
    print(f"  persistence MAE            : {mae(pers_pairs):6.1f} ug/m3"
          f"   (n={len(pers_pairs)})")
    print(f"  climatology MAE            : {mae(clim_pairs):6.1f} ug/m3")
    print(f"  raw CAMS MAE               : {mae(cams_pairs):6.1f} ug/m3")
    print("=" * 52)
    print(f"  period: {days[0]} to {days[-1]}")

    # write what we have so the daily job has something to append to
    config.DATA.mkdir(exist_ok=True)
    with open(config.DAILY_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=config.COLUMNS)
        w.writeheader()
        for d in days:
            w.writerow({
                "date": d,
                "obs_pm25": round(obs[d], 2),
                "obs_hours": "",
                "cams_pm25": round(cams[d], 2),
                "cams_issue_date": "",   # unknown for backfill, see note
                "temp_mean": "", "rh_mean": "",
                "wind_speed_mean": "", "wind_dir_mean": "",
                "fire_count": "",
                "ingested_at": datetime.now(IST).isoformat(timespec="seconds"),
            })
    print(f"\nwrote {config.DAILY_CSV} ({len(days)} rows)")
    print("\nNOTE: cams_issue_date is blank for these backfilled rows.")
    print("They are usable for BASELINES but NOT for training, since")
    print("we cannot prove which forecast run they came from. Rows")
    print("written by the daily job carry a real issue date and are")
    print("the ones the model trains on.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
