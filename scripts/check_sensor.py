"""One-time: compare candidate sensors for the same pollutant
at one station and report which is still reporting.

OpenAQ can expose several sensors per parameter; some are
retired but still serve their old series."""

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "code"))
import config

IST = timezone(timedelta(hours=5, minutes=30))
BASE = "https://api.openaq.org/v3"


def get(path, **params):
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url, headers={"X-API-Key": config.OPENAQ_KEY})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 401:
            print("401 Unauthorized: OPENAQ_KEY is missing or wrong.")
            sys.exit(1)
        if e.code == 404:
            return None
        raise


def daily_rows(sensor_id, start, end):
    """Daily aggregates, filtered client-side as well as by query.

    v3 drops unknown query params silently and returns the whole
    series, so the row count alone cannot be trusted.
    """
    out, page = [], 1
    while page <= 5:
        data = get(f"/sensors/{sensor_id}/days",
                   date_from=start.isoformat(),
                   date_to=end.isoformat(),
                   limit=1000, page=page)
        got = (data or {}).get("results", [])
        if not got:
            break
        out.extend(got)
        if len(got) < 1000:
            break
        page += 1

    kept = []
    for r in out:
        day = ((r.get("period") or {}).get("datetimeFrom")
               or {}).get("local", "")[:10]
        if day and start.isoformat() <= day <= end.isoformat():
            kept.append((day, r.get("value")))
    return len(out), kept


def describe(sensor_id, start, end):
    print("=" * 58)
    print(f"sensor {sensor_id}")
    print("=" * 58)

    meta = get(f"/sensors/{sensor_id}")
    if not meta or not meta.get("results"):
        print("  not found")
        return None
    s = meta["results"][0]

    first = (s.get("datetimeFirst") or {}).get("local", "")
    last = (s.get("datetimeLast") or {}).get("local", "")
    param = (s.get("parameter") or {}).get("name", "?")
    units = (s.get("parameter") or {}).get("units", "?")

    print(f"  parameter  : {param} ({units})")
    print(f"  first seen : {first or '?'}")
    print(f"  last seen  : {last or '?'}")

    returned, kept = daily_rows(sensor_id, start, end)
    print(f"  rows returned by API       : {returned}")
    print(f"  rows actually inside window: {len(kept)}")
    if returned and len(kept) < returned:
        print("  NOTE server returned rows outside the requested")
        print("       window; counts below are the filtered ones.")

    vals = [v for _, v in kept if v is not None]
    if vals:
        print(f"  value range: {min(vals):.1f} to {max(vals):.1f}")

    # Is it still reporting? Anything quiet for >14 days is stale.
    stale_days = None
    if last:
        try:
            seen = datetime.fromisoformat(last).date()
            stale_days = (datetime.now(IST).date() - seen).days
            state = "LIVE" if stale_days <= 14 else f"STALE ({stale_days}d)"
            print(f"  status     : {state}")
        except ValueError:
            pass
    print()
    return {"id": sensor_id, "n": len(kept), "last": last,
            "stale_days": stale_days}


def main():
    ids = sys.argv[1:]
    if not ids:
        print(__doc__)
        return 1

    end = datetime.now(IST).date()
    start = end - timedelta(days=97)
    print(f"window: {start} to {end}\n")

    rows = [r for r in (describe(int(i), start, end) for i in ids) if r]
    if not rows:
        return 1

    print("=" * 58)
    print("RECOMMENDATION")
    print("=" * 58)

    # Recency is a filter, not a tiebreak. A sensor that stopped
    # reporting is useless however much history it holds.
    live = [r for r in rows
            if r["stale_days"] is not None and r["stale_days"] <= 14]

    if not live:
        print("  No candidate is still reporting. Check the station,")
        print("  or fall back to the CPCB CCR bulk download.")
        for r in rows:
            print(f"  {r['id']:<12} last={r['last']}")
        return 1

    best = max(live, key=lambda r: r["n"])
    for r in rows:
        tag = "" if r in live else "  [STALE, excluded]"
        mark = "  <-- use this one" if r["id"] == best["id"] else ""
        print(f"  {r['id']:<12} {r['n']:>4} days in window"
              f"  last={r['last']}{tag}{mark}")
    print()
    print(f"Set OPENAQ_PM25_SENSOR_ID = {best['id']} in code/config.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
