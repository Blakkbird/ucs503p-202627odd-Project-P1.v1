#!/usr/bin/env python3
"""One-time: find the OpenAQ location and sensor ids for the
configured station. Results go into code/config.py."""

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "code"))
import config

BASE = "https://api.openaq.org/v3"


def get(path, **params):
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url, headers={"X-API-Key": config.OPENAQ_KEY})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def main():
    if not config.OPENAQ_KEY:
        print("Set OPENAQ_KEY first. Free key from "
              "https://explore.openaq.org after signing up.")
        return 1

    # Search within 25 km of the configured coordinates.
    data = get("/locations",
               coordinates=f"{config.LAT},{config.LON}",
               radius=25000,
               limit=50)

    results = data.get("results", [])
    if not results:
        print("No stations found near the configured coordinates.")
        return 1

    print(f"{len(results)} station(s) within 25 km:\n")
    for loc in results:
        pm25 = [s for s in loc.get("sensors", [])
                if s.get("parameter", {}).get("name") == "pm25"]
        print(f" location_id={loc['id']:<8} {loc.get('name')}")
        print(f" provider : {loc.get('provider', {}).get('name')}")
        print(f" last seen: {loc.get('datetimeLast', {}).get('local')}")
        for s in pm25:
            print(f" >>> pm25 sensor_id={s['id']}")
        print()

    print("Copy the location_id and the pm25 sensor_id of the")
    print(f"station matching {config.STATION_NAME!r} into")
    print("code/config.py, then run scripts/bootstrap.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
