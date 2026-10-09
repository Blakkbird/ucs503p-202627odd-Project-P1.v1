"""Regenerate the numbers and plot data behind the prototype report.

Every figure quoted in project-report-prototype-stage/main.tex comes
from here, out of data/ as it stands when this runs, so the report
cannot drift from the record the way hand-copied numbers did in
docs/ earlier in the project. Run it, then rebuild the PDF:

    python scripts/report_figures.py
    cd project-report-prototype-stage && latexmk -pdf main.tex

Writes, under project-report-prototype-stage/data/:

    numbers.tex     \\newcommand macros for every quoted figure
    season.dat      Oct-Nov 2025: observed, Pawan, persistence
    ratio.dat       CAMS over observed, by calendar month
"""

import csv
import json
import math
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))

import config
import evaluate
import features

OUT = ROOT / "project-report-prototype-stage" / "data"

# The 2025 burning season, drawn day by day in the report.
SEASON = (date(2025, 10, 1), date(2025, 11, 30))

# CPCB band edges used for the advisory check: above 60 is worse
# than Satisfactory, above 90 is Poor or worse.
MODERATE = 60.0
POOR = 90.0


def macro(name, value):
    return f"\\newcommand{{\\{name}}}{{{value}}}\n"


def fmt(x, places=2):
    return f"{x:.{places}f}"


def pct(x):
    return f"{x * 100:.1f}"


def mae(pairs):
    pairs = [(a, b) for a, b in pairs if a is not None and b is not None]
    return sum(abs(a - b) for a, b in pairs) / len(pairs), len(pairs)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    samples = features.build(use_weather=True)
    runs = evaluate.backtest(samples)
    by_day = {s.day: s for s in samples}
    out = []

    # --- backtest, overall and by subset --------------------------
    groups = {
        "All": runs,
        "Calm": [r for r in runs if r["day"].month
                 not in config.BURNING_MONTHS],
        "Burn": [r for r in runs if r["day"].month
                 in config.BURNING_MONTHS],
        "Live": [r for r in runs if r["live"]],
    }
    for label, subset in groups.items():
        days = [r["day"] for r in subset]
        rows = [by_day[d] for d in days]
        model, n = mae([(r["truth"], r["model"]) for r in subset])
        textbook, _ = mae([(s.y, s.persistence) for s in rows])
        oper, _ = mae([(s.y, s.persistence_op) for s in rows])
        cams, _ = mae([(s.y, math.expm1(s.x[s.names.index("cams_log")]))
                       for s in rows])
        out += [macro(f"N{label}", n),
                macro(f"Model{label}", fmt(model)),
                macro(f"Text{label}", fmt(textbook)),
                macro(f"Oper{label}", fmt(oper)),
                macro(f"Cams{label}", fmt(cams)),
                macro(f"SkillOp{label}", pct((oper - model) / oper)),
                macro(f"SkillTx{label}", pct((textbook - model) / textbook)),
                macro(f"LossTx{label}", pct((model - textbook) / textbook))]

    out += [macro("BacktestFirst", runs[0]["day"].strftime("%-d %B %Y")),
            macro("BacktestLast", runs[-1]["day"].strftime("%-d %B %Y"))]

    # --- the advisory question: was a Poor day seen coming? -------
    poor = [r for r in runs if r["truth"] > POOR]
    flagged = [r for r in runs if r["model"] > POOR]
    caught = [r for r in poor if r["model"] > POOR]
    out += [macro("PoorDays", len(poor)),
            macro("PoorCaught", len(caught)),
            macro("PoorFlagged", len(flagged))]

    # The same question one band lower, where there are enough
    # days to compare against: worse than Satisfactory.
    hi = [r for r in runs if r["truth"] > MODERATE]
    oper_hi = [r for r in runs if (by_day[r["day"]].persistence_op or 0)
               > MODERATE]
    out += [macro("ModDays", len(hi)),
            macro("ModCaught", sum(1 for r in hi if r["model"] > MODERATE)),
            macro("ModFlagged", sum(1 for r in runs
                                    if r["model"] > MODERATE)),
            macro("ModOperCaught", sum(1 for r in oper_hi
                                       if r["truth"] > MODERATE)),
            macro("ModOperFlagged", len(oper_hi)),
            macro("MaxForecast", fmt(max(r["model"] for r in runs), 0))]

    # the worst observed days, and what Pawan said the day before
    worst = sorted(runs, key=lambda r: -r["truth"])[:5]
    peak = worst[0]
    out += [macro("PeakDay", peak["day"].strftime("%-d %B %Y")),
            macro("PeakObs", fmt(peak["truth"], 0)),
            macro("PeakModel", fmt(peak["model"], 0)),
            macro("TopFiveRatio", fmt(
                sum(r["model"] for r in worst)
                / sum(r["truth"] for r in worst) * 100, 0))]

    # --- the live record ------------------------------------------
    with open(config.PREDICTIONS_JSON) as f:
        records = json.load(f)["predictions"]
    first = date.fromisoformat(records[0]["date"])
    last = date.fromisoformat(records[-1]["date"])
    expected = (last - first).days + 1
    scored = [r for r in records if r.get("actual") is not None]
    inside = [r for r in scored if "interval" in r
              and r["interval"][0] <= r["actual"] <= r["interval"][1]]
    live_mae = sum(abs(r["error"]) for r in scored) / len(scored)
    out += [macro("LiveFirst", first.strftime("%-d %B")),
            macro("LiveLast", last.strftime("%-d %B")),
            macro("LiveExpected", expected),
            macro("LiveIssued", len(records)),
            macro("LiveScored", len(scored)),
            macro("LiveMAE", fmt(live_mae)),
            macro("LiveBand", sum(1 for r in scored if r.get("band_hit"))),
            macro("LiveInside", len(inside))]

    # --- the table itself -----------------------------------------
    with open(config.DAILY_CSV, newline="") as f:
        table = list(csv.DictReader(f))
    observed = [r for r in table if r["obs_pm25"]]
    thin = [r for r in observed if r["obs_hours"]
            and float(r["obs_hours"]) < config.MIN_OBS_HOURS]
    span = (date.fromisoformat(table[-1]["date"])
            - date.fromisoformat(table[0]["date"])).days + 1
    out += [macro("Rows", len(table)),
            macro("RowsFirst", date.fromisoformat(
                table[0]["date"]).strftime("%-d %B %Y")),
            macro("RowsObserved", len(observed)),
            macro("RowsThin", len(thin)),
            macro("RowsLive", sum(1 for r in table
                                  if r["cams_issue_date"])),
            macro("RowsSpan", span),
            macro("Usable", len(features.usable(samples)))]

    # CAMS over observed, by calendar month, both years pooled
    month = defaultdict(lambda: [0.0, 0.0])
    for r in observed:
        if not r["cams_pm25"]:
            continue
        m = int(r["date"][5:7])
        month[m][0] += float(r["cams_pm25"])
        month[m][1] += float(r["obs_pm25"])
    with open(OUT / "ratio.dat", "w") as f:
        f.write("month ratio\n")
        for m in range(1, 13):
            cams, obs = month[m]
            f.write(f"{m} {cams / obs:.3f}\n")
    ratios = {m: c / o for m, (c, o) in month.items()}
    out += [macro("RatioLow", fmt(min(ratios.values()), 1)),
            macro("RatioHigh", fmt(max(ratios.values()), 1))]

    # the 2025 season, day by day
    with open(OUT / "season.dat", "w") as f:
        f.write("day observed model persistence\n")
        for r in runs:
            if SEASON[0] <= r["day"] <= SEASON[1]:
                s = by_day[r["day"]]
                f.write(f"{(r['day'] - SEASON[0]).days} {r['truth']:.1f} "
                        f"{r['model']:.1f} {s.persistence_op:.1f}\n")

    (OUT / "numbers.tex").write_text(
        "% Generated by scripts/report_figures.py. Do not edit.\n"
        + "".join(out))
    print(f"wrote {len(out)} figures and 2 data files to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
