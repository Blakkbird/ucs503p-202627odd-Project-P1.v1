"""Render the public pages from whatever is currently on record.

Everything here is generated, never hand-edited. data/*.json is
the single source of truth for every number the site shows, so
the pages cannot drift away from what the model actually did --
which is exactly what happened to the prose in docs/index.md
before this existed.

Three things come out:

  docs/forecast.md         tomorrow's number, the recent record,
                           how the last few forecasts turned out
  docs/results.md          the backtest, the baselines it is
                           measured against, and what is wrong
                           with it
  docs/dashboard/data.json everything the dashboard draws. The
                           page itself (index.html, dashboard.js)
                           is written by hand and never changes
                           from day to day; only this file does

Named pages.py rather than the more obvious site.py, because
`site` is a standard library module that Python has already
imported by the time this runs, and shadowing it means the import
silently resolves to the wrong thing.

The chart is an SVG built here rather than by a charting library
in the browser. It is one more thing that has to keep working
unattended, and a few hundred characters of path data has fewer
ways to fail than a CDN.
"""

import json
import math
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config
import evaluate
import features
from model import Ridge

IST = timezone(timedelta(hours=5, minutes=30))
DOCS = config.ROOT / "docs"

# CPCB National AQI colours, so the page agrees with every other
# air quality display a reader in India has seen.
BAND_COLOUR = {
    "Good": "#5ba829",
    "Satisfactory": "#9dc63d",
    "Moderate": "#f0c419",
    "Poor": "#f08019",
    "Very Poor": "#e0403c",
    "Severe": "#8b2c28",
}

# Days of history behind the chart. Long enough to show the model
# tracking a real swing, short enough to stay readable on a phone.
CHART_DAYS = 45


def read(path):
    """A JSON file, or None if it is missing or unreadable."""
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def scale(lo, hi, size, pad):
    """Map a data range onto a pixel range, avoiding a zero span."""
    span = (hi - lo) or 1.0
    return lambda v: pad + (v - lo) / span * (size - 2 * pad)


def chart(observed, forecasts, width=760, height=260):
    """Observed PM2.5 with the forecasts laid over it.

    `observed` is [(date, value)] and `forecasts` is
    [(date, value, low, high)]. Returns an SVG string sized by
    viewBox so it scales with the column rather than the window.
    """
    if not observed and not forecasts:
        return "<p>Nothing on record yet.</p>"

    days = [d for d, _ in observed] + [d for d, _, _, _ in forecasts]
    values = ([v for _, v in observed]
              + [v for _, v, _, _ in forecasts]
              + [h for _, _, _, h in forecasts])
    first, last = min(days), max(days)
    top = max(values) * 1.15
    pad = 34

    x = scale(0, (last - first).days, width, pad)
    y = scale(0, top, height, pad)

    def px(day):
        return x((day - first).days)

    def py(value):
        return height - y(value)

    out = [(f'<svg viewBox="0 0 {width} {height}" class="pawan-chart" '
            f'role="img" aria-label="Observed and forecast PM2.5">')]

    # Horizontal guides, labelled in micrograms.
    step = 10 if top <= 60 else 25 if top <= 150 else 50
    level = step
    while level < top:
        out.append(f'<line x1="{pad}" y1="{py(level):.1f}" '
                   f'x2="{width - pad}" y2="{py(level):.1f}" '
                   f'class="pawan-grid"/>')
        out.append(f'<text x="{pad - 6}" y="{py(level) + 4:.1f}" '
                   f'class="pawan-axis" text-anchor="end">{level}</text>')
        level += step

    # Forecast uncertainty, drawn first so everything sits on top.
    if len(forecasts) > 1:
        upper = " ".join(f"{px(d):.1f},{py(h):.1f}"
                         for d, _, _, h in forecasts)
        lower = " ".join(f"{px(d):.1f},{py(lo):.1f}"
                         for d, _, lo, _ in reversed(forecasts))
        out.append(f'<polygon points="{upper} {lower}" class="pawan-band"/>')

    if len(observed) > 1:
        line = " ".join(f"{px(d):.1f},{py(v):.1f}" for d, v in observed)
        out.append(f'<polyline points="{line}" class="pawan-observed"/>')

    if len(forecasts) > 1:
        line = " ".join(f"{px(d):.1f},{py(v):.1f}"
                        for d, v, _, _ in forecasts)
        out.append(f'<polyline points="{line}" class="pawan-forecast"/>')

    for day, value, _, _ in forecasts:
        out.append(f'<circle cx="{px(day):.1f}" cy="{py(value):.1f}" '
                   f'r="3" class="pawan-dot"/>')

    for day in (first, last):
        out.append(f'<text x="{px(day):.1f}" y="{height - 8}" '
                   f'class="pawan-axis" text-anchor="middle">'
                   f'{day.strftime("%d %b")}</text>')

    out.append("</svg>")
    return "\n".join(out)


def missing(day, reason=None, last=None):
    """Shown in place of the card when tomorrow has no forecast.

    The page used to fall back to the newest record it had, under a
    heading that still said tomorrow, so a run that failed on a
    Tuesday kept showing Monday's number as though it were
    Wednesday's. Showing nothing is better than showing something
    stale, and saying why is better than both.
    """
    why = (f"The daily job could not issue one: {reason}."
           if reason else "The daily job has not issued one yet.")
    if last:
        when = date.fromisoformat(last["date"]).strftime("%A %d %B")
        why += (f" The last forecast on record was for {when}, at "
                f"{last['pm25']:.0f} &micro;g/m&sup3;.")
    return (
        '<div class="pawan-card" style="border-left-color:#9e9e9e">\n'
        f'  <div class="pawan-when">{day.strftime("%A %d %B")}</div>\n'
        '  <div class="pawan-value">No forecast</div>\n'
        f'  <div class="pawan-note">{why}</div>\n'
        "</div>\n"
    )


def headline(record):
    """The card at the top of the page: one number, read at a glance."""
    colour = BAND_COLOUR.get(record["band"], "#666")
    day = date.fromisoformat(record["date"])
    low, high = record.get("interval", [None, None])
    span = (f"{low:.0f} to {high:.0f}" if low is not None else "not sized")

    return (
        f'<div class="pawan-card" style="border-left-color:{colour}">\n'
        f'  <div class="pawan-when">{day.strftime("%A %d %B")}</div>\n'
        f'  <div class="pawan-value">{record["pm25"]:.0f}'
        f'<span class="pawan-unit">&micro;g/m&sup3;</span></div>\n'
        f'  <div class="pawan-band-name" style="color:{colour}">'
        f'{record["band"]}</div>\n'
        f'  <div class="pawan-note">likely range {span} &middot; '
        f'issued {record["issued"]}</div>\n'
        f"</div>\n"
    )


def outcomes_table(records, limit=10):
    """The last few forecasts with what actually happened."""
    scored = [r for r in records if r.get("actual") is not None]
    if not scored:
        return "_No forecast has been scored yet._\n"

    lines = ["| Day | Forecast | Observed | Error | Band |",
             "| --- | ---: | ---: | ---: | :--- |"]
    for r in scored[-limit:][::-1]:
        mark = "correct" if r.get("band_hit") else "missed"
        lines.append(f"| {r['date']} | {r['pm25']:.1f} | {r['actual']:.1f} "
                     f"| {r['error']:+.1f} | {r['band']} ({mark}) |")
    return "\n".join(lines) + "\n"


def forecast_page(predictions, samples, today=None):
    """docs/forecast.md -- what the service is actually for.

    `today` is a parameter so the tests can pin it. Left to the
    clock, a test written with September data quietly stopped
    drawing its chart once September fell out of the window, and
    that failure would have blocked the daily commit.
    """
    records = predictions.get("predictions", []) if predictions else []
    by_day = {r["date"]: r for r in records}

    today = today or datetime.now(IST).date()
    tomorrow = today + timedelta(days=1)
    record = by_day.get(tomorrow.isoformat())
    if record:
        top = headline(record)
    else:
        status = (predictions or {}).get("status") or {}
        reason = (status.get("reason")
                  if status.get("target") == tomorrow.isoformat() else None)
        earlier = [r for r in records if r["date"] < tomorrow.isoformat()]
        top = missing(tomorrow, reason, earlier[-1] if earlier else None)

    cutoff = today - timedelta(days=CHART_DAYS)
    observed = [(s.day, s.y) for s in samples
                if s.y is not None and s.day >= cutoff]
    drawn = [(date.fromisoformat(r["date"]), r["pm25"],
              r.get("interval", [r["pm25"], r["pm25"]])[0],
              r.get("interval", [r["pm25"], r["pm25"]])[1])
             for r in records if date.fromisoformat(r["date"]) >= cutoff]

    scored = [r for r in records if r.get("actual") is not None]
    if scored:
        mae = sum(abs(r["error"]) for r in scored) / len(scored)
        hits = sum(1 for r in scored if r.get("band_hit"))
        live = (f"Since the service started issuing forecasts it has made "
                f"**{len(records)}** of them, **{len(scored)}** of which have "
                f"an observation to be checked against. On those, the mean "
                f"absolute error is **{mae:.1f} &micro;g/m&sup3;** and the "
                f"AQI band was right **{hits} times out of {len(scored)}**.\n")
    else:
        live = ("No forecast has been checked against an observation yet. "
                "The station publishes about three days late, so the first "
                "few take a while to score.\n")

    stamp = (predictions or {}).get("generated_at", "unknown")
    return f"""# Tomorrow in Patiala

[Open the live dashboard](dashboard/index.html) for the fire map,
the full history and a panel to try different inputs.

{top}

{chart(observed, drawn)}

The solid line is what the station at Model Town measured. The
dotted line is what Pawan said the day before, and the shaded
area is the range it gave. Observations arrive about three days
behind, so the most recent forecasts have nothing to sit against
yet.

## How it has done so far

{live}

That is the live record, not the backtest. It is short, and it
only covers a quiet time of year. [The full evaluation](results.md)
is the number to argue with.

{outcomes_table(records)}

A forecast is written once and never revised. When the
observation for that day finally publishes it is filed beside the
original, untouched. Rewriting yesterday's forecast after
yesterday happened is the easiest way to build a system that
looks far better than it is.

<small>Generated from `data/predictions.json` at {stamp}.</small>
"""


def weights_table(model):
    """Standardised coefficients, which are comparable to each other."""
    if not model:
        return ""
    pairs = sorted(zip(model.get("names", []), model.get("coef", [])),
                   key=lambda kv: -abs(kv[1]))
    lines = ["| Feature | Weight |", "| --- | ---: |"]
    for name, weight in pairs:
        lines.append(f"| `{name}` | {weight:+.3f} |")
    return "\n".join(lines) + "\n"


# Skill targets from the proposal, against operational persistence.
TARGETS = {"calm": 0.10, "burning": 0.20}
SEASONS = {"calm": "Calm (Dec to Sep)", "burning": "Burning (Oct, Nov)"}


def gain(entry):
    """Skill over operational persistence for one score block."""
    model = (entry or {}).get("model")
    ref = (entry or {}).get("persistence_operational")
    if not model or not ref or not ref["mae"]:
        return None
    return (ref["mae"] - model["mae"]) / ref["mae"]


def season_table(metrics):
    """One row per season, against the target the proposal set."""
    seasons = metrics.get("by_season") or {}
    head = ("| Season | Days | Pawan MAE | Operational persistence MAE "
            "| Skill | Target |")
    lines = [head, "| --- | ---: | ---: | ---: | ---: | :--- |"]
    for key, label in SEASONS.items():
        entry = seasons.get(key) or {}
        target = TARGETS[key]
        skill = gain(entry)
        if skill is None:
            lines.append(f"| {label} | 0 | - | - | - "
                         f"| {target * 100:.0f}%, not yet scored |")
            continue
        verdict = "met" if skill >= target else "not met"
        lines.append(
            f"| {label} | {entry['model']['n']} "
            f"| {entry['model']['mae']:.2f} "
            f"| {entry['persistence_operational']['mae']:.2f} "
            f"| {skill * 100:+.1f}% | {target * 100:.0f}%, {verdict} |")
    return "\n".join(lines) + "\n"


def live_line(metrics):
    """The live-only score, which no archive has had a hand in."""
    live = (metrics.get("by_provenance") or {}).get("live")
    skill = gain(live)
    if skill is None:
        return ""
    return (f"On the **{live['model']['n']}** days whose CAMS forecast "
            f"was recorded live rather than read back from an archive, "
            f"Pawan's MAE is **{live['model']['mae']:.2f}** against "
            f"{live['persistence_operational']['mae']:.2f} for "
            f"operational persistence, **{skill * 100:+.1f}%**. No "
            f"archive has flattered those days, so if this figure and "
            f"the totals drift apart, this is the one to believe.\n")


def caveats(metrics):
    """What is wrong with the numbers, worked out from the numbers.

    This used to be fixed prose, and it said `burning` had never
    fired. The moment the history reached back into October that
    would have become false, on a page whose whole job is to be
    the honest one.
    """
    burn = ((metrics.get("by_season") or {}).get("burning") or {})
    counts = metrics.get("counts") or {}
    notes = []

    if not burn.get("model"):
        notes.append(
            "- **`burning` has never fired.** No scored day falls in "
            "October or November, so the burning-season flag carries no "
            "weight yet and the 20% target rests on a feature the model "
            "has not seen. `fire_log` does vary and does carry weight, "
            "which is the part of the mechanism that has been tested.")
        notes.append(
            "- **The window is calm season only.** The band accuracy in "
            "particular is close to meaningless here, because almost "
            "every day falls in Good and a method that guessed Good every "
            "time would score nearly as well.")
    else:
        back = counts.get("burning_backfilled", 0)
        live = counts.get("burning_live", 0)
        n = burn["model"]["n"]
        days = "day is" if n == 1 else "days are"
        notes.append(
            f"- **Burning season is a small sample.** {n} burning-season "
            f"{days} scored: {back} read back from archives and {live} "
            f"recorded live. That is one or two seasons at most, and a "
            f"dry year, a wet one or a shift in when the stubble is burnt "
            f"would each move these numbers.")
        notes.append(
            "- **Band accuracy only means much in burning season.** On "
            "calm days almost everything falls in Good, and a method "
            "that guessed Good every time would score nearly as well.")

    notes.append(
        "- **Archive rows are mildly optimistic.** Rows read back from "
        "archives take CAMS and weather from series stitched out of the "
        "opening hours of successive model runs, which sit a little "
        "closer to what happened than a forecast issued a day ahead. "
        "The live-only figure, where there is one, is the check on how "
        "much that flatters the totals.")
    notes.append(
        "- **The feature set was chosen on calm-season data.** Every "
        "change was made for a stated reason and not only because it "
        "scored better, but the reasons and the scores were looked at "
        "together. This year's burning season, scored live as it "
        "happens, is the test nothing here was tuned against.")
    return "\n".join(notes) + "\n"


def results_page(metrics, model):
    """docs/results.md -- the numbers, including the awkward ones."""
    if not metrics:
        return "# Results\n\n_No backtest on record. Run `make eval`._\n"

    overall = metrics["overall"]
    window = metrics["window"]
    skill = metrics.get("skill", {})

    labels = {
        "model": "Pawan",
        "persistence": "Persistence (textbook)",
        "persistence_operational": "Persistence (operational)",
        "climatology": "Climatology",
        "raw_cams": "Raw CAMS",
    }
    rows = ["| Method | n | MAE | RMSE | Bias | Band correct |",
            "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for key, label in labels.items():
        got = overall.get(key)
        if not got:
            continue
        mark = "**" if key == "model" else ""
        rows.append(
            f"| {mark}{label}{mark} | {got['n']} | {mark}{got['mae']:.2f}{mark} "
            f"| {got['rmse']:.2f} | {got['bias']:+.2f} "
            f"| {got['band_hit_rate'] * 100:.0f}% |")
    table = "\n".join(rows)

    def verdict(key, name):
        gain = skill.get(key)
        if gain is None:
            return f"- Against {name}: not measured.\n"
        word = "better" if gain > 0 else "worse"
        return f"- Against {name}: **{abs(gain) * 100:.1f}% {word}** on MAE.\n"

    return f"""# Results

Walk-forward backtest over {window['first']} to {window['last']},
{overall['model']['n']} days. The model is refitted from scratch
before each day and only ever sees days strictly before the one
it is predicting. There is no shuffled train/test split anywhere
in this project; the rows are a time series and shuffling them
would let the model read its own future.

{table}

## By season

The targets are set per season because the two are different
problems. Calm-season air moves slowly and persistence is hard to
beat; burning season is when a forecast is worth having.

{season_table(metrics)}
{live_line(metrics)}
## Skill

{verdict("operational", "operational persistence")}{verdict("textbook", "textbook persistence")}
The two baselines are both persistence, and the difference
between them is the whole argument.

**Operational persistence** is the best a person could do at
08:00 using what the CPCB feed has actually published by then,
which is a reading about four days old. That is the same
information Pawan has, so it is a fair comparison, and it is what
the forecast is worth to somebody deciding whether to run
outside tomorrow.

**Textbook persistence** uses yesterday's reading. Nobody has
yesterday's reading when the forecast goes out. It is reported
because it is the figure quoted in the proposal, and because it
marks the ceiling: the gap between the two baselines is the cost
of the publication lag, and closing it needs a faster feed rather
than a better model.

## What the model weighs

Fitted on {metrics.get('min_train', '?')}+ rows, in log space,
with the penalty chosen inside each fit on a held-out tail.
Weights are on standardised inputs, so their sizes can be
compared with each other but not read as physics.

{weights_table(model)}

## What is wrong with this

Worth saying plainly.

{caveats(metrics)}
<small>Generated from `data/metrics.json` and `data/model.json`.</small>
"""


# --- dashboard --------------------------------------------------

# What each band means for a person deciding about tomorrow. Worded
# after the health statements CPCB publishes with the National AQI,
# shortened to fit under a number.
ADVICE = {
    "Good": "Clean air. Nothing to plan around.",
    "Satisfactory": ("Fine for almost everyone. People who are unusually "
                     "sensitive may notice slight discomfort."),
    "Moderate": ("People with asthma, heart or lung conditions, children "
                 "and older adults may feel it. Go easier on long outdoor "
                 "exercise."),
    "Poor": ("Most people may feel some discomfort over long exposure. "
             "Sensitive groups should cut down time outdoors."),
    "Very Poor": ("Long exposure can bring on breathing trouble. Skip "
                  "outdoor exercise and keep windows shut at the worst "
                  "hours."),
    "Severe": ("Affects healthy people too. Stay indoors where you can; "
               "sensitive groups should not go out."),
}

# The model's inputs, grouped the way a reader would name them.
# Wind's two components are one thing to a person, and so is a
# fire count and its burning-season interaction, if one is ever
# fitted. Anything not listed here is shown under its own name.
GROUPS = {
    "cams_log": "cams", "burn_cams": "cams",
    "obs_recent_log": "station", "burn_obs": "station",
    "fire_log": "fires", "burn_fire": "fires",
    "rh": "rh",
    "temp": "temp",
    "wind_speed": "wind_speed",
    "wind_u": "wind_dir", "wind_v": "wind_dir", "burn_wind_u": "wind_dir",
    "burning": "season",
}
GROUP_LABELS = {
    "cams": "CAMS global forecast",
    "station": "Latest station reading",
    "fires": "Fires detected yesterday",
    "rh": "Humidity",
    "temp": "Temperature",
    "wind_speed": "Wind speed",
    "wind_dir": "Wind direction",
    "season": "Burning season",
}

# A fire counts as upwind of the station when it lies within this
# many degrees of the bearing the wind is coming from, and within
# this distance. Shown on the map only; the model reads the plain
# count over the whole box.
UPWIND_HALF_ANGLE = 30
UPWIND_RANGE_KM = 400

# How many recent forecasts the track record strip shows.
RECORD_TILES = 30


def bearing_km(lat1, lon1, lat2, lon2):
    """Compass bearing and great-circle distance from point 1 to 2."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = (math.cos(p1) * math.sin(p2)
         - math.sin(p1) * math.cos(p2) * math.cos(dl))
    bearing = math.degrees(math.atan2(y, x)) % 360
    h = (math.sin((p2 - p1) / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2)
    return bearing, 2 * 6371.0 * math.asin(math.sqrt(h))


def upwind(bearing, wind_from):
    """True when a bearing sits inside the upwind wedge."""
    if wind_from is None:
        return False
    gap = abs((bearing - wind_from + 180) % 360 - 180)
    return gap <= UPWIND_HALF_ANGLE


def explain(model, x):
    """Each input's push on the forecast, grouped and ordered.

    For a linear model this is exact rather than an estimate: the
    fitted response is the intercept plus one term per input, so
    the terms are the explanation. Under a log target they add in
    log space, which means each one multiplies the forecast, and
    `effect` is that multiplier minus one (+0.25 is 25% higher).
    """
    terms = {}
    for name, coef, mean, dev, value in zip(model.names, model.coef,
                                            model.means, model.devs, x):
        key = GROUPS.get(name, name)
        terms[key] = terms.get(key, 0.0) + coef * (value - mean) / dev
    out = []
    for key, term in terms.items():
        effect = math.expm1(term) if model.log_target else term
        out.append({"key": key, "label": GROUP_LABELS.get(key, key),
                    "term": round(term, 6), "effect": round(effect, 4)})
    return sorted(out, key=lambda t: -abs(t["term"]))


def r1(value):
    return None if value is None else round(value, 1)


def history_series(rows, records, backtest, tomorrow):
    """Day-by-day columns for the history chart, oldest first.

    Observed is everything the station published, thin days
    included but flagged, since a chart with holes where the thin
    days were would look like an outage that never happened.
    """
    measured = {}
    for key, row in rows.items():
        value = features.num(row.get("obs_pm25"))
        if value is not None:
            measured[key] = (value, features.num(row.get("obs_hours")))
    cams = {k: features.num(r.get("cams_pm25")) for k, r in rows.items()}
    back = {r["date"]: r["model"] for r in (backtest or {}).get("runs", [])}
    live = {r["date"]: r for r in records}

    known = [k for k in rows if cams.get(k) is not None or k in measured]
    if not known:
        return None
    day, last = date.fromisoformat(min(known)), tomorrow
    out = {k: [] for k in ("dates", "observed", "thin", "cams", "backtest",
                           "forecast", "low", "high")}
    while day <= last:
        key = day.isoformat()
        value, hours = measured.get(key, (None, None))
        rec = live.get(key) or {}
        low, high = rec.get("interval") or (None, None)
        out["dates"].append(key)
        out["observed"].append(r1(value))
        out["thin"].append(hours is not None and hours < config.MIN_OBS_HOURS)
        out["cams"].append(r1(cams.get(key)))
        out["backtest"].append(r1(back.get(key)))
        out["forecast"].append(r1(rec.get("pm25")))
        out["low"].append(r1(low))
        out["high"].append(r1(high))
        day += timedelta(days=1)
    return out


def live_record(records):
    """How the issued forecasts have done, in the terms the page uses."""
    scored = [r for r in records if r.get("actual") is not None]
    out = {"issued": len(records), "scored": len(scored),
           "first": records[0]["date"] if records else None}
    if not scored:
        return out
    out["mae"] = round(sum(abs(r["error"]) for r in scored) / len(scored), 2)
    out["band_hits"] = sum(1 for r in scored if r.get("band_hit"))

    # Operational persistence on exactly the same days, from the
    # reading each forecast had in front of it when it was issued.
    pairs = [((r.get("inputs") or {}).get("persistence_operational"),
              r["actual"]) for r in scored]
    pairs = [(p, a) for p, a in pairs if p is not None]
    if pairs:
        out["persistence_mae"] = round(
            sum(abs(p - a) for p, a in pairs) / len(pairs), 2)
        out["persistence_n"] = len(pairs)

    ranged = [r for r in scored if r.get("interval")]
    if ranged:
        out["with_range"] = len(ranged)
        out["in_range"] = sum(1 for r in ranged
                              if r["interval"][0] <= r["actual"]
                              <= r["interval"][1])
    return out


def backtest_summary(metrics):
    """The backtest, reduced to what the dashboard prints."""
    if not metrics:
        return None
    overall = metrics.get("overall") or {}

    def mae(block, key):
        got = (block or {}).get(key)
        return got["mae"] if got else None

    seasons = {}
    for key, entry in (metrics.get("by_season") or {}).items():
        skill = gain(entry)
        if skill is None:
            continue
        seasons[key] = {"days": entry["model"]["n"],
                        "mae": mae(entry, "model"),
                        "persistence_mae": mae(entry,
                                               "persistence_operational"),
                        "skill": round(skill, 4),
                        "target": TARGETS.get(key)}
    return {"first": (metrics.get("window") or {}).get("first"),
            "last": (metrics.get("window") or {}).get("last"),
            "days": (overall.get("model") or {}).get("n"),
            "mae": mae(overall, "model"),
            "persistence_mae": mae(overall, "persistence_operational"),
            "cams_mae": mae(overall, "raw_cams"),
            "skill": (metrics.get("skill") or {}).get("operational"),
            "seasons": seasons}


def fire_map(fires, target):
    """Recent fires with an upwind flag, against tomorrow's wind."""
    days = sorted((fires or {}).get("days") or {}, reverse=True)
    if not days:
        return None
    raw = target.raw if target else {}
    wind_from, speed = raw.get("wind_dir"), raw.get("wind_speed")

    points, counts = [], []
    for age, day in enumerate(days):
        n_up = 0
        for lat, lon, frp, conf in fires["days"][day]:
            bearing, km = bearing_km(config.LAT, config.LON, lat, lon)
            up = upwind(bearing, wind_from) and km <= UPWIND_RANGE_KM
            n_up += up
            # [lat, lon, fire power, upwind, days before the newest,
            #  low confidence]
            points.append([lat, lon, frp, int(up), age, int(conf == "l")])
        counts.append({"day": day, "fires": len(fires["days"][day]),
                       "upwind": n_up})

    w, s_, e, n = (float(v) for v in config.FIRMS_BBOX.split(","))
    return {"days": counts, "points": points,
            "wind_from": wind_from, "wind_speed": speed,
            "half_angle": UPWIND_HALF_ANGLE, "range_km": UPWIND_RANGE_KM,
            "bbox": [w, s_, e, n]}


def pipeline_health(rows, records, samples, model, today):
    """The numbers that show the pipeline is running, not just built."""
    observed = [k for k, r in rows.items() if r.get("obs_pm25")]
    stamps = [r.get("ingested_at") for r in rows.values()
              if r.get("ingested_at")]
    tomorrow = today + timedelta(days=1)
    newest = max(observed) if observed else None

    # Days in a row, ending tomorrow, with a forecast on record.
    # More telling than a total: it resets the first morning the
    # job fails to issue one.
    issued = {r["date"] for r in records}
    streak, day = 0, tomorrow
    while day.isoformat() in issued:
        streak += 1
        day -= timedelta(days=1)
    return {
        "last_ingest": max(stamps) if stamps else None,
        "newest_obs": newest,
        "obs_age_days": ((today - date.fromisoformat(newest)).days
                         if newest else None),
        "usual_age_days": config.OBS_LATENCY_DAYS + 1,
        "stale_after_days": config.OBS_STALENESS_LIMIT_DAYS,
        "first_forecast": records[0]["date"] if records else None,
        "issued": len(records),
        "streak": streak,
        "rows": len(rows),
        "first_row": min(rows) if rows else None,
        "usable_rows": len(features.usable(samples)),
        "inputs": len((model or {}).get("names") or []),
    }


def dashboard_data(predictions, samples, rows, metrics, model,
                   backtest=None, fires=None, today=None):
    """Everything docs/dashboard/ draws, as one JSON-ready dict.

    `today` is a parameter for the same reason as in forecast_page.
    """
    today = today or datetime.now(IST).date()
    tomorrow = today + timedelta(days=1)
    records = sorted((predictions or {}).get("predictions", []),
                     key=lambda r: r["date"])
    record = next((r for r in records
                   if r["date"] == tomorrow.isoformat()), None)
    target = next((s for s in samples if s.day == tomorrow), None)

    status = (predictions or {}).get("status") or {}
    reason = (status.get("reason")
              if status.get("target") == tomorrow.isoformat() else None)

    out = {
        "generated_at": datetime.now(IST).isoformat(timespec="seconds"),
        "today": today.isoformat(),
        "tomorrow": tomorrow.isoformat(),
        "station": {"name": config.STATION_NAME, "city": config.CITY,
                    "lat": config.LAT, "lon": config.LON},
        "bands": [{"name": name, "upper": None if math.isinf(edge) else edge,
                   "colour": BAND_COLOUR[name], "advice": ADVICE[name]}
                  for edge, name in evaluate.BANDS],
        "forecast": record,
        "missing_reason": None if record else (
            reason or "the daily job has not issued one yet"),
    }

    # What tomorrow's forecast was built from, and the model that
    # turned it into a number. The page's what-if panel rebuilds
    # the vector from `raw` and checks it against `x` before it
    # trusts its own arithmetic.
    if target is not None:
        out["inputs"] = {"names": target.names, "x": target.x,
                         "raw": target.raw, "burning": target.burning,
                         "complete": target.complete}
    if model and target is not None and model.get("names") == target.names:
        fitted = Ridge.from_dict(model)
        out["model"] = {k: model[k] for k in ("names", "coef", "means",
                                              "devs", "intercept",
                                              "log_target", "alpha")}
        out["model"]["interactions"] = features.INTERACTIONS
        out["model"]["groups"] = GROUPS
        out["model"]["typical"] = (math.expm1(fitted.intercept)
                                   if fitted.log_target else fitted.intercept)
        if target.complete:
            out["model"]["now"] = fitted.predict_one(target.x)
            out["why"] = explain(fitted, target.x)

    out["history"] = history_series(rows, records, backtest, tomorrow)
    out["record"] = live_record([r for r in records
                                 if r["date"] <= tomorrow.isoformat()])
    out["recent"] = [
        {"date": r["date"], "pm25": r["pm25"], "band": r["band"],
         "actual": r.get("actual"),
         "actual_band": (evaluate.band(r["actual"])
                         if r.get("actual") is not None else None)}
        for r in records if r["date"] <= tomorrow.isoformat()
    ][-RECORD_TILES:]
    out["backtest"] = backtest_summary(metrics)
    out["fires"] = fire_map(fires, target)
    out["health"] = pipeline_health(rows, records, samples, model, today)
    return out


def write_dashboard(data, path=None):
    """Write the dashboard's data file.

    allow_nan is off because JSON has no NaN and the browser's
    parser rejects the whole file over a single one. Better to
    fail here, where the run log shows it, than on the page.
    """
    path = Path(path or config.DASHBOARD_JSON)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, allow_nan=False,
                               separators=(",", ":")))


def main():
    metrics = read(config.METRICS_JSON)
    model = read(config.MODEL_JSON)
    predictions = read(config.PREDICTIONS_JSON)
    samples = features.build()

    DOCS.mkdir(exist_ok=True)
    written = []
    for name, body in (("forecast.md", forecast_page(predictions, samples)),
                       ("results.md", results_page(metrics, model))):
        (DOCS / name).write_text(body)
        written.append(name)

    print(f"wrote {', '.join(f'docs/{n}' for n in written)}")

    # The dashboard comes last and is not allowed to fail the run.
    # This step sits in front of the daily commit, so an exception
    # here would throw away the morning's observations along with
    # the page. Instead the page gets told what went wrong and
    # says so, and the log carries the traceback.
    try:
        data = dashboard_data(predictions, samples, features.load(),
                              metrics, model, read(config.BACKTEST_JSON),
                              read(config.FIRES_JSON))
        write_dashboard(data)
        print(f"wrote {config.DASHBOARD_JSON.relative_to(config.ROOT)}")
    except Exception as e:  # noqa: BLE001 -- see above
        import traceback
        traceback.print_exc()
        print(f"ERROR: dashboard data not built: {e}")
        write_dashboard({"error": f"{type(e).__name__}: {e}",
                         "generated_at": datetime.now(IST).isoformat(
                             timespec="seconds")})
    return 0


if __name__ == "__main__":
    sys.exit(main())
