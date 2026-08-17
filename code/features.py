"""Turn data/daily.csv into rows a model can be fitted on.

The hard part here is not arithmetic, it is bookkeeping. A row for
target day D is only honest if every number in it existed on the
morning of D-1, when the job that produces the forecast actually
runs. Two things make that awkward:

  * the CPCB feed lags, so the freshest observation on D-1 is
    roughly D-4 rather than D-2 (config.OBS_LATENCY_DAYS);
  * rows written by scripts/bootstrap.py have no cams_issue_date,
    so we cannot prove which model run they came from.

Both are handled here rather than being left for the model to trip
over later.
"""

import csv
import math
import sys
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config

# Features that exist for every row. The weather columns were only
# added to the daily job later and are blank for most of the
# backfilled history, so they are opt-in until the backfill has
# been run (scripts/backfill_history.py).
CORE = ["cams_log", "obs_recent", "obs_recent_log", "obs_mean7",
        "obs_age", "doy_sin", "doy_cos", "burning"]
WEATHER = ["temp", "rh", "wind_speed", "wind_u", "wind_v", "fire_log"]


@dataclass
class Sample:
    """One target day, ready to be fitted or scored."""

    day: date
    x: list[float]
    y: float | None            # observed daily mean; None until it lands
    live: bool                 # forecast provenance is provable
    persistence: float | None  # obs[D-1]: the textbook baseline
    persistence_op: float | None  # freshest obs actually available on D-1
    names: list[str] = field(default_factory=list)

    @property
    def burning(self):
        return self.day.month in config.BURNING_MONTHS

    @property
    def usable(self):
        """Has a label and a full feature vector."""
        return self.y is not None and all(v is not None for v in self.x)


def num(cell):
    """CSV cell to float, or None when it is blank or junk."""
    try:
        return float(cell)
    except (TypeError, ValueError):
        return None


def load(path=None):
    """daily.csv as {date: row}, dropping anything undated."""
    path = path or config.DAILY_CSV
    if not Path(path).exists():
        return {}
    with open(path, newline="") as f:
        return {r["date"]: r for r in csv.DictReader(f) if r.get("date")}


def _observed_upto(obs, cutoff, window):
    """Observations on the `window` days ending at `cutoff`.

    Returns them oldest-first. Gaps are simply absent rather than
    interpolated -- a missing day is information, not something to
    paper over.
    """
    out = []
    for k in range(window - 1, -1, -1):
        got = obs.get(cutoff - timedelta(days=k))
        if got is not None:
            out.append(got)
    return out


def build(rows=None, use_weather=False):
    """Build one Sample per target day, oldest first.

    `use_weather` adds the meteorology columns. Leave it off until
    scripts/backfill_history.py has filled them in, otherwise
    almost every row loses its feature vector and the training set
    collapses to a handful of days.
    """
    rows = load() if rows is None else rows
    names = CORE + (WEATHER if use_weather else [])

    obs = {}
    for key, row in rows.items():
        value = num(row.get("obs_pm25"))
        if value is not None:
            obs[date.fromisoformat(key)] = value

    samples = []
    for key in sorted(rows):
        day = date.fromisoformat(key)
        row = rows[key]

        cams = num(row.get("cams_pm25"))
        if cams is None or cams <= 0:
            continue  # no forecast to correct, so there is no row

        # Everything below is read as of the morning of D-1.
        issue = day - timedelta(days=1)
        cutoff = issue - timedelta(days=config.OBS_LATENCY_DAYS)

        recent = _observed_upto(obs, cutoff, 1)
        week = _observed_upto(obs, cutoff, 7)
        obs_recent = recent[-1] if recent else None
        obs_mean7 = sum(week) / len(week) if week else None

        # How stale that most recent reading is. When the feed has
        # been down for a week the model should be able to see it.
        age = None
        if obs_recent is not None:
            for k in range(config.OBS_LATENCY_DAYS + 8):
                if obs.get(cutoff - timedelta(days=k)) is not None:
                    age = float(k + config.OBS_LATENCY_DAYS + 1)
                    break

        doy = day.timetuple().tm_yday
        values = {
            "cams_log": math.log1p(cams),
            "obs_recent": obs_recent,
            "obs_recent_log": (math.log1p(obs_recent)
                               if obs_recent is not None else None),
            "obs_mean7": obs_mean7,
            "obs_age": age,
            "doy_sin": math.sin(2 * math.pi * doy / 365.25),
            "doy_cos": math.cos(2 * math.pi * doy / 365.25),
            "burning": 1.0 if day.month in config.BURNING_MONTHS else 0.0,
        }

        if use_weather:
            speed = num(row.get("wind_speed_mean"))
            bearing = num(row.get("wind_dir_mean"))
            fires = num(row.get("fire_count"))
            # Wind splits into components so the model can tell a
            # northwesterly (residue smoke) from a southeasterly of
            # the same strength.
            if speed is not None and bearing is not None:
                rad = math.radians(bearing)
                u, v = -speed * math.sin(rad), -speed * math.cos(rad)
            else:
                u = v = None
            values.update({
                "temp": num(row.get("temp_mean")),
                "rh": num(row.get("rh_mean")),
                "wind_speed": speed,
                "wind_u": u,
                "wind_v": v,
                "fire_log": (math.log1p(fires)
                             if fires is not None else None),
            })

        samples.append(Sample(
            day=day,
            x=[values[n] for n in names],
            y=obs.get(day),
            live=bool(row.get("cams_issue_date")),
            persistence=obs.get(day - timedelta(days=1)),
            persistence_op=obs_recent,
            names=names,
        ))

    return samples


def usable(samples):
    return [s for s in samples if s.usable]


def coverage(samples):
    """Per-feature count of rows that actually have the value.

    Cheap way to see which column is costing us training rows
    before blaming the model for a small n.
    """
    if not samples:
        return {}
    names = samples[0].names
    return {n: sum(1 for s in samples if s.x[i] is not None)
            for i, n in enumerate(names)}


def main():
    """`python code/features.py` prints what the dataset looks like."""
    for weather in (False, True):
        built = build(use_weather=weather)
        ready = usable(built)
        label = "core + weather" if weather else "core only"
        print(f"\n{label}: {len(built)} candidate rows, "
              f"{len(ready)} usable, "
              f"{sum(1 for s in ready if s.live)} of them live")
        for name, got in coverage(built).items():
            flag = "  <-- sparse" if got < len(built) * 0.8 else ""
            print(f"    {name:16s} {got:3d}/{len(built)}{flag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
