"""Turn data/daily.csv into rows a model can be fitted on.

The hard part here is not arithmetic, it is bookkeeping. A row for
target day D is only honest if every number in it existed on the
morning of D-1, when the job that produces the forecast actually
runs. Three things make that awkward:

  * the CPCB feed lags, by an amount that has changed over the
    semester, so a row is always built for one stated reading age
    (config.OBS_MIN_AGE, OBS_MAX_AGE) and the forecast picks the
    age it can actually have;
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
#                carried no information and only cost a parameter.
#                (Age is handled differently now: every model is
#                fitted at one age, see build)
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

# Burning-season interactions. None of these is fitted by default.
# `burning` on its own can only shift the whole season up or down;
# these let the season change how much the model leans on each
# input. scripts/compare_models.py backtests them against the plain
# set, and one only moves into the fitted list if it earns it on
# burning-season days without costing more than that on calm ones.
#
#   burn_fire     smoke is a burning-season mechanism; in June a
#                 fire count is mostly noise
#   burn_wind_u   the stubble is west and northwest of Patiala, so
#                 the eastward wind component is what carries it in
#   burn_obs      a four-day-old reading says less when the level
#                 can double inside a week
#   burn_cams     CAMS gets its fire emissions from satellites and
#                 may be worth more, or less, once they matter
INTERACTIONS = {
    "burn_fire": ("burning", "fire_log"),
    "burn_wind_u": ("burning", "wind_u"),
    "burn_obs": ("burning", "obs_recent_log"),
    "burn_cams": ("burning", "cams_log"),
}


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
    obs_age: float | None = None    # days between that reading and `day`
    horizon: int = 1                # days between issue and `day`
    names: list[str] = field(default_factory=list)
    raw: dict = field(default_factory=dict)  # readings x was built from

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


def transform(raw, burning, names):
    """Model inputs from the plain readings they are built from.

    `raw` holds the readings in their own units: micrograms for
    CAMS and the station, a count for fires, degrees and km/h for
    the weather. Any of them can be None, and whatever depends on
    a missing one comes out None too.

    Kept as one small function on purpose. The dashboard's "what
    if" panel does the same arithmetic in JavaScript, so that
    sliding a reading moves the forecast exactly the way the model
    would. Two copies of a formula drift apart, so the page checks
    its copy against the vector this function produced before it
    lets anyone touch a slider. Change something here and that
    check is what will notice.
    """
    def log1p(v):
        return None if v is None else math.log1p(v)

    speed, bearing = raw.get("wind_speed"), raw.get("wind_dir")
    # Wind splits into components so the model can tell a
    # northwesterly (residue smoke) from a southeasterly of the
    # same strength.
    if speed is not None and bearing is not None:
        rad = math.radians(bearing)
        u, v = -speed * math.sin(rad), -speed * math.cos(rad)
    else:
        u = v = None

    values = {
        "cams_log": log1p(raw.get("cams")),
        "obs_recent_log": log1p(raw.get("obs_recent")),
        "burning": 1.0 if burning else 0.0,
        "temp": raw.get("temp"),
        "rh": raw.get("rh"),
        "wind_speed": speed,
        "wind_u": u,
        "wind_v": v,
        "fire_log": log1p(raw.get("fires")),
    }
    for name, (left, right) in INTERACTIONS.items():
        a, b = values.get(left), values.get(right)
        values[name] = None if a is None or b is None else a * b
    return [values[n] for n in names]


def _readings(rows):
    """The station's readings, three ways.

    `measured` is everything the station published, and is what a
    target day's label and the site's history chart come from.
    `obs` drops the thin days, and is what gets fed forward as a
    feature or a baseline: a day assembled from nine hours is
    untrustworthy as an input for the same reason it is
    untrustworthy as a label. `hours` is the count behind each one.
    """
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
    return measured, obs, hours


def default_age(horizon=1):
    """The reference age, pushed back by however far ahead we look."""
    return config.OBS_REFERENCE_AGE + horizon - 1


def freshest_age(rows, target, horizon=1):
    """Age of the freshest valid reading on file for `target`.

    Counted from the target day, so with the feed a day behind a
    forecast for tomorrow gets 2. Never less than horizon + 1: the
    issue day is not over when the job runs, so even a reading for
    it that looks complete is not one. None when nothing usable is
    on file within OBS_MAX_AGE, which is the case where no
    forecast should go out at all.
    """
    rows = load() if rows is None else rows
    _, obs, _ = _readings(rows)
    for age in range(horizon + 1, config.OBS_MAX_AGE + horizon):
        if obs.get(target - timedelta(days=age)) is not None:
            return age
    return None


def build(rows=None, use_weather=True, extra=None, age=None, horizon=1):
    """Build one Sample per target day, oldest first.

    `age` fixes how old the station reading in every row is,
    counted from the target day. Every row in one build uses the
    same age, which is the point: a model fitted on two-day-old
    readings has learnt how much a two-day-old reading is worth,
    and should not be handed a five-day-old one at forecast time.
    The forecast finds the age it can have (freshest_age) and asks
    for samples at that age; the backtest does the same for each
    age it scores. Left as None it is the reference age.

    `horizon` is how many days ahead of the issue day the target
    is. One for tomorrow; the outlook uses two and three. It moves
    the issue day back, which moves the fire count back with it,
    and the youngest allowed reading.

    `use_weather` is on by default now that the meteorology
    backfill has been run. Turning it off reproduces the earlier
    CAMS-plus-persistence model, which is the ablation quoted in
    the report; it is not something the daily job should do.

    `extra` names INTERACTIONS to append. Each is the product of
    two columns already in the row, so it adds nothing the row did
    not already know at issue time. Left as None it is the set the
    shipped model uses, config.SHIPPED_EXTRA; pass () for none.
    """
    rows = load() if rows is None else rows
    extra = config.SHIPPED_EXTRA if extra is None else extra
    age = default_age(horizon) if age is None else age
    if age < horizon + 1:
        raise ValueError(f"a reading {age} days old is not published "
                         f"{horizon} day(s) ahead of the target")
    names = CORE + (WEATHER if use_weather else []) + list(extra)
    measured, obs, hours = _readings(rows)

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

        # Everything below is read as of the issue day.
        issue = day - timedelta(days=horizon)

        # Exactly `age` days back, or nothing. There used to be a
        # walk-back here for when the cutoff day had not published
        # yet. That job now belongs to the forecast, which looks
        # for the freshest age it can get and asks for a model fitted
        # at that age; a row that walked back would hand this model a
        # reading older than the ones it was fitted on.
        obs_day = day - timedelta(days=age)
        obs_recent = obs.get(obs_day)

        raw = {"cams": cams, "obs_recent": obs_recent,
               "obs_day": obs_day.isoformat() if obs_recent is not None
               else None}

        if use_weather:
            # Walk back from the last day whose count was complete
            # at issue time until one is found. A few days of gap
            # is tolerable; beyond a week the row simply has no
            # fire feature and drops out of the fit.
            burn_day = issue - timedelta(days=config.FIRE_LATENCY_DAYS)
            recent_fires, fire_day = None, None
            for k in range(7):
                got = fires.get(burn_day - timedelta(days=k))
                if got is not None:
                    recent_fires = got
                    fire_day = burn_day - timedelta(days=k)
                    break
            raw.update({
                "temp": num(row.get("temp_mean")),
                "rh": num(row.get("rh_mean")),
                "wind_speed": num(row.get("wind_speed_mean")),
                "wind_dir": num(row.get("wind_dir_mean")),
                "fires": recent_fires,
                "fire_day": fire_day.isoformat() if fire_day else None,
            })

        samples.append(Sample(
            day=day,
            x=transform(raw, day.month in config.BURNING_MONTHS, names),
            y=measured.get(day),
            live=bool(row.get("cams_issue_date")),
            persistence=obs.get(day - timedelta(days=1)),
            persistence_op=obs_recent,
            obs_hours=hours.get(day),
            obs_age=float(age) if obs_recent is not None else None,
            horizon=horizon,
            names=names,
            raw=raw,
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
