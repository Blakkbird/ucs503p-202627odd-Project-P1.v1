"""Turn data/daily.csv into rows a model can be fitted on.

The hard part here is not arithmetic, it is bookkeeping. A row for
target day D is only honest if every number in it existed on the
morning of D-1, when the job that produces the forecast actually
runs. Three things make that awkward:

  * the CPCB feed lags, so the freshest observation on D-1 is
    roughly D-4 rather than D-2 (config.OBS_LATENCY_DAYS);
  * rows written by scripts/bootstrap.py have no cams_issue_date,
    so we cannot prove which model run they came from;
  * some days are published with only a handful of hours behind
    them, and a 14-hour mean is not the quantity we are trying to
    predict (config.MIN_OBS_HOURS).

All three are handled here rather than being left for the model to
trip over later.
"""

import csv
import math
import sys
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config

# The columns the model is actually fitted on.
#
# This list is shorter than it was. The week 5 review dropped four
# things, each for its own reason:
#
#   obs_recent   duplicated obs_recent_log, which split one signal
#                across two coefficients that then fought
#   obs_age      constant at 4.0 once the feed was healthy, so it
#                carried no information and only cost a parameter
#   obs_mean7    a weekly mean adds nothing once yesterday's
#                reading and today's meteorology are both present
#   doy_sin/cos  with four months of data these cannot tell
#                seasonality from trend. They had learnt "PM2.5
#                falls through the monsoon" and would have kept
#                extrapolating that straight into burning season
#
# What is left is either the thing being corrected, the station's
# own recent level, or a physical driver of dispersion.
CORE = ["cams_log", "obs_recent_log", "burning"]
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
    obs_hours: float | None = None  # hours behind y, when known
    obs_age: float | None = None    # days between issue and that reading
    names: list[str] = field(default_factory=list)

    @property
    def burning(self):
        return self.day.month in config.BURNING_MONTHS

    @property
    def complete(self):
        """Every feature has a value, so the row can be predicted."""
        return all(v is not None for v in self.x)

    @property
    def valid_target(self):
        """The label is present and is a real 24-hour mean.

        Days assembled from too few hours are dropped rather than
        kept and down-weighted. There are only a handful of them,
        and weighting them correctly would be harder to defend
        than simply leaving them out.
        """
        if self.y is None:
            return False
        return self.obs_hours is None or self.obs_hours >= config.MIN_OBS_HOURS

    @property
    def usable(self):
        """Fit-ready: a trustworthy label and a full feature vector."""
        return self.valid_target and self.complete


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


def build(rows=None, use_weather=True):
    """Build one Sample per target day, oldest first.

    `use_weather` is on by default now that the meteorology
    backfill has been run. Turning it off reproduces the earlier
    CAMS-plus-persistence model, which is the ablation quoted in
    the report; it is not something the daily job should do.
    """
    rows = load() if rows is None else rows
    names = CORE + (WEATHER if use_weather else [])

    # Two views of the observations. `measured` is everything the
    # station published, and is what a target day's label and the
    # site's history chart come from. `obs` drops the thin days,
    # and is what gets fed forward as a feature or a baseline: a
    # day assembled from nine hours is untrustworthy as an input
    # for the same reason it is untrustworthy as a label.
    measured, obs, hours = {}, {}, {}
    for key, row in rows.items():
        value = num(row.get("obs_pm25"))
        if value is None:
            continue
        day = date.fromisoformat(key)
        count = num(row.get("obs_hours"))
        measured[day] = value
        hours[day] = count
        if count is None or count >= config.MIN_OBS_HOURS:
            obs[day] = value

    # Fire detections are recorded against the day they happened,
    # which means a target day's own count does not exist yet when
    # the forecast for it goes out. Read lagged, per FIRE_LATENCY_DAYS.
    fires = {}
    for key, row in rows.items():
        count = num(row.get("fire_count"))
        if count is not None:
            fires[date.fromisoformat(key)] = count

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
        obs_recent = recent[-1] if recent else None

        # How stale that reading is. Not a feature any more, but
        # the daily job still publishes it, so a bad forecast can
        # be read back against a half-dead feed later.
        age = None
        if obs_recent is not None:
            for k in range(config.OBS_LATENCY_DAYS + 8):
                if obs.get(cutoff - timedelta(days=k)) is not None:
                    age = float(k + config.OBS_LATENCY_DAYS + 1)
                    break

        values = {
            "cams_log": math.log1p(cams),
            "obs_recent_log": (math.log1p(obs_recent)
                               if obs_recent is not None else None),
            "burning": 1.0 if day.month in config.BURNING_MONTHS else 0.0,
        }

        if use_weather:
            speed = num(row.get("wind_speed_mean"))
            bearing = num(row.get("wind_dir_mean"))
            # Walk back from the last day whose count was complete
            # at issue time until one is found. A few days of gap
            # is tolerable; beyond a week the row simply has no
            # fire feature and drops out of the fit.
            burn_day = issue - timedelta(days=config.FIRE_LATENCY_DAYS)
            recent_fires = None
            for k in range(7):
                got = fires.get(burn_day - timedelta(days=k))
                if got is not None:
                    recent_fires = got
                    break
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
                "fire_log": (math.log1p(recent_fires)
                             if recent_fires is not None else None),
            })

        samples.append(Sample(
            day=day,
            x=[values[n] for n in names],
            y=measured.get(day),
            live=bool(row.get("cams_issue_date")),
            persistence=obs.get(day - timedelta(days=1)),
            persistence_op=obs_recent,
            obs_hours=hours.get(day),
            obs_age=age,
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
        thin = sum(1 for s in built
                   if s.y is not None and not s.valid_target)
        label = "core + weather" if weather else "core only"
        print(f"\n{label}: {len(built)} candidate rows, "
              f"{len(ready)} usable, "
              f"{sum(1 for s in ready if s.live)} of them live, "
              f"{thin} dropped as thin")
        for name, got in coverage(built).items():
            flag = "  <-- sparse" if got < len(built) * 0.8 else ""
            print(f"    {name:16s} {got:3d}/{len(built)}{flag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
