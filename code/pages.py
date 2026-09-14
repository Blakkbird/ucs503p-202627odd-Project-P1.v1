"""Render the public pages from whatever is currently on record.

Everything here is generated, never hand-edited. data/*.json is
the single source of truth for every number the site shows, so
the pages cannot drift away from what the model actually did --
which is exactly what happened to the prose in docs/index.md
before this existed.

Two pages come out:

  docs/forecast.md   tomorrow's number, the recent record, how
                     the last few forecasts turned out
  docs/results.md    the backtest, the baselines it is measured
                     against, and what is wrong with it

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
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config
import features

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


def headline(record):
    """The card at the top of the page: one number, read at a glance."""
    if not record:
        return ("!!! warning \"No forecast on record\"\n\n"
                "    The daily job has not issued one for tomorrow yet.\n")

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


def forecast_page(predictions, samples):
    """docs/forecast.md -- what the service is actually for."""
    records = predictions.get("predictions", []) if predictions else []
    by_day = {r["date"]: r for r in records}

    tomorrow = (datetime.now(IST).date() + timedelta(days=1)).isoformat()
    latest = by_day.get(tomorrow) or (records[-1] if records else None)

    cutoff = datetime.now(IST).date() - timedelta(days=CHART_DAYS)
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

{headline(latest)}

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

Worth saying plainly, because all of it will matter by November.

- **The window is short and quiet.** Every scored day is calm
  season. The band accuracy in particular is close to meaningless
  here, because almost every day falls in Good and a method that
  guessed Good every time would score nearly as well.
- **`burning` has never fired.** No training row falls in October
  or November, so the burning-season flag carries no weight yet
  and the 20% target for that season rests on a feature the model
  has not seen. `fire_log` does vary and does carry weight, which
  is the part of the mechanism that has been tested.
- **Meteorology starts late.** Open-Meteo's archive reaches back
  about 92 days, so the earliest rows have no weather and drop
  out of the fit. The usable set grows by one row a day.
- **The feature set was chosen on this window.** Every change was
  made for a stated reason and not only because it scored better,
  but the reasons and the scores were looked at together, and a
  40-day window is not enough to separate the two. The honest
  test is how this holds up in October, on days nothing here has
  been tuned against.

<small>Generated from `data/metrics.json` and `data/model.json`.</small>
"""


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
    return 0


if __name__ == "__main__":
    sys.exit(main())
