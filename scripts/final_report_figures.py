"""Every number, table and chart in the final report.

Reads the files the daily job commits and writes, under
project-report-final/:

    data/numbers.tex      \\newcommand macros for every quoted figure
    data/*.tex            tables, as LaTeX fragments
    figures/*.pdf         charts

Nothing in the report is typed in by hand, so running this again
after a later ingest brings every figure up to date at once.

    pip install matplotlib
    python scripts/final_report_figures.py
"""

import csv
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))
import config

OUT = ROOT / "project-report-final"
DATA = OUT / "data"
FIGS = OUT / "figures"

BLUE, GREY, ORANGE, INK = "#1b62a6", "#8a939b", "#c2410c", "#1f2933"
plt.rcParams.update({
    "font.size": 9, "axes.titlesize": 9, "axes.labelsize": 9,
    "legend.fontsize": 8, "xtick.labelsize": 8, "ytick.labelsize": 8,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": INK, "axes.labelcolor": INK,
    "xtick.color": INK, "ytick.color": INK, "savefig.bbox": "tight",
})


def load(name):
    with open(config.DATA / name) as f:
        return json.load(f)


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def f2(x):
    return f"{x:.2f}"


def f1(x):
    return f"{x:.1f}"


def pct(x):
    return f"{x * 100:+.1f}\\%"


def plain_pct(x):
    return f"{x * 100:.0f}\\%"


def long_date(d):
    d = date.fromisoformat(d) if isinstance(d, str) else d
    return f"{d.day} {d:%B %Y}"


VERY_POOR = 120.0   # above this a day is Very Poor or worse
POOR = 90.0         # above this a day is Poor or worse


def flags(pairs, cut):
    """(days above cut, of those flagged, forecasts above cut, false)."""
    bad = [(t, p) for t, p in pairs if t > cut]
    hit = sum(1 for t, p in bad if p > cut)
    called = [(t, p) for t, p in pairs if p > cut]
    false = sum(1 for t, p in called if t <= cut)
    return len(bad), hit, len(called), false


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    FIGS.mkdir(parents=True, exist_ok=True)
    m = {}

    with open(config.DAILY_CSV, newline="") as f:
        rows = list(csv.DictReader(f))
    metrics = load("metrics.json")
    board = load("leaderboard.json")
    predictions = load("predictions.json")
    runs = load("backtest.json")["runs"]

    # --- the record -----------------------------------------------
    obs_rows = [r for r in rows if num(r["obs_pm25"]) is not None]
    snapshot = max(r["date"] for r in obs_rows)
    m["SnapshotDate"] = long_date(snapshot)
    m["TableRows"] = len(rows)
    m["FirstReading"] = long_date(obs_rows[0]["date"])
    hours = [num(r["obs_hours"]) for r in obs_rows
             if num(r["obs_hours"]) is not None]
    first, last = date.fromisoformat(obs_rows[0]["date"]), \
        date.fromisoformat(snapshot)
    span = (last - first).days + 1
    m["DataAvailability"] = plain_pct(sum(hours) / (24 * span))
    valid = sum(1 for h in hours if h >= config.MIN_OBS_HOURS)
    m["ValidDays"] = valid
    m["SpanDays"] = span
    m["ValidShare"] = plain_pct(valid / span)

    # --- headline backtest (reference age) -------------------------
    o = metrics["overall"]
    m["BtFirst"] = long_date(metrics["window"]["first"])
    m["BtLast"] = long_date(metrics["window"]["last"])
    m["BtDays"] = o["model"]["n"]
    m["RefAge"] = metrics["obs_age"]
    m["MaePawan"] = f2(o["model"]["mae"])
    m["MaePers"] = f2(o["persistence_operational"]["mae"])
    m["MaeCams"] = f2(o["raw_cams"]["mae"])
    m["MaeClim"] = f2(o["climatology"]["mae"]) if o.get("climatology") \
        else "--"
    m["SkillAll"] = pct(metrics["skill"]["operational"])
    seasons = metrics["by_season"]
    for key, label in (("calm", "Calm"), ("burning", "Burn")):
        s = seasons[key]
        mod, per = s["model"]["mae"], s["persistence_operational"]["mae"]
        m[f"Days{label}"] = s["model"]["n"]
        m[f"Mae{label}"] = f2(mod)
        m[f"Pers{label}"] = f2(per)
        m[f"Skill{label}"] = pct((per - mod) / per)
        m[f"Cams{label}"] = f2(s["raw_cams"]["mae"])
    live = metrics["by_provenance"]["live"]
    m["LiveBtDays"] = live["model"]["n"]
    m["LiveBtMae"] = f2(live["model"]["mae"])
    m["LiveBtPers"] = f2(live["persistence_operational"]["mae"])
    m["BandHit"] = plain_pct(o["model"]["band_hit_rate"])

    # --- by reading age (model lab) --------------------------------
    by_age = {a["age"]: a for a in board["by_age"]}
    lines = []
    for age in sorted(by_age):
        a = by_age[age]
        lines.append(f"{age} days & {a['days']} & {f2(a['mae'])} & "
                     f"{f2(a['persistence_mae'])} & {pct(a['skill'])} & "
                     f"{pct(a['calm_skill'])} & {pct(a['burning_skill'])} "
                     "\\\\")
    (DATA / "by_age.tex").write_text("\n".join(lines) + "\n")
    for age in (2, 3, 4):
        if age in by_age:
            word = {2: "Two", 3: "Three", 4: "Four"}[age]
            m[f"CalmSkill{word}"] = pct(by_age[age]["calm_skill"])
            m[f"BurnSkill{word}"] = pct(by_age[age]["burning_skill"])

    # --- leaderboard ----------------------------------------------
    models = sorted(board["models"], key=lambda x: x["overall"]["mae"])
    live_board = board.get("live") or {}
    lines = []
    for x in models:
        sk = x.get("skill") or {}
        lv = live_board.get(x["key"])
        name = x["label"].replace("&", "\\&")
        if x.get("shipped"):
            name = f"\\textbf{{{name}}}"
        lv_text = f"{f1(lv['mae'])} ({lv['n']})" if lv else "--"
        burn = sk.get("burning")
        lines.append(
            f"{name} & {x['kind']} & {f2(x['overall']['mae'])} & "
            f"{pct(sk['overall']) if sk.get('overall') is not None else '--'} & "
            f"{pct(burn) if burn is not None else '--'} & {lv_text} \\\\")
    (DATA / "leaderboard.tex").write_text("\n".join(lines) + "\n")
    m["LabDays"] = board["days"]
    m["LabModels"] = len(models)
    m["LabDate"] = long_date(board["backtest_on"])
    shipped = next(x for x in models if x.get("shipped"))
    m["LabShippedMae"] = f2(shipped["overall"]["mae"])
    rec = next((x for x in models if x["key"] == "ridge_recent"), None)
    if rec:
        m["LabRecentMae"] = f2(rec["overall"]["mae"])
        m["LabRecentBurn"] = pct(rec["skill"]["burning"])
        m["LabShippedBurn"] = pct(shipped["skill"]["burning"])
    best_tree = min((x for x in models if x["kind"] in ("tree", "neural")),
                    key=lambda x: x["overall"]["mae"])
    m["LabBestBenchmark"] = best_tree["label"]
    m["LabBestBenchmarkMae"] = f2(best_tree["overall"]["mae"])
    rule = board["rule"]
    m["RuleBurnGain"] = f"{rule['burning_gain'] * 100:.0f}"
    m["RuleCalmCost"] = f"{rule['calm_cost'] * 100:.0f}"
    m["RuleRobust"] = f"{rule['robust_cost'] * 100:.0f}"
    m["RuleLiveDays"] = rule["live_days"]

    # --- outlook and the likely range ------------------------------
    lines = []
    for h in sorted(metrics["horizons"], key=int):
        b = metrics["horizons"][h]
        cov = b["coverage"]["overall"]
        lines.append(f"{b['horizon']} & {b['age']} days & {b['days']} & "
                     f"{f2(b['model']['mae'])} & {f2(b['persistence']['mae'])}"
                     f" & {pct(b['skill'])} & {cov['held']} of {cov['days']}"
                     " \\\\")
    (DATA / "outlook.tex").write_text("\n".join(lines) + "\n")
    cov = metrics["horizons"]["1"]["coverage"]
    m["RangeHeld"] = cov["overall"]["held"]
    m["RangeDays"] = cov["overall"]["days"]
    m["RangeRate"] = plain_pct(cov["overall"]["rate"])
    m["RangeBurnHeld"] = cov["burning"]["held"]
    m["RangeBurnDays"] = cov["burning"]["days"]
    m["RangeBurnRate"] = plain_pct(cov["burning"]["rate"])

    # --- live record ----------------------------------------------
    recs = predictions["predictions"]
    scored = [r for r in recs if r.get("actual") is not None]
    m["LiveIssued"] = len(recs)
    m["LiveFirst"] = long_date(recs[0]["date"])
    m["LiveScored"] = len(scored)
    m["LiveMae"] = f1(sum(abs(r["error"]) for r in scored) / len(scored))
    pers = [(r["inputs"]["persistence_operational"], r["actual"])
            for r in scored
            if r["inputs"].get("persistence_operational") is not None]
    m["LivePersMae"] = f1(sum(abs(p - a) for p, a in pers) / len(pers))
    m["LivePersDays"] = len(pers)
    cal = [r for r in scored if r.get("range_method") == "calibrated"]
    m["LiveRangeDays"] = len(cal)
    m["LiveRangeHeld"] = sum(1 for r in cal
                             if r["interval"][0] <= r["actual"]
                             <= r["interval"][1])
    # pipeline success: target days since the first with a forecast
    have = {r["date"] for r in recs}
    d0 = date.fromisoformat(recs[0]["date"])
    d1 = date.fromisoformat(recs[-1]["date"])
    days = [(d0 + timedelta(days=k)).isoformat()
            for k in range((d1 - d0).days + 1)]
    m["PipeDays"] = len(days)
    m["PipeIssued"] = sum(1 for d in days if d in have)
    m["PipeRate"] = plain_pct(m["PipeIssued"] / len(days))

    # --- category recall and false alarms --------------------------
    pairs = [(r["truth"], r["model"]) for r in runs]
    for cut, word in ((VERY_POOR, "VP"), (POOR, "Poor")):
        n_bad, hit, n_called, false = flags(pairs, cut)
        m[f"{word}Days"] = n_bad
        m[f"{word}Hit"] = hit
        m[f"{word}Called"] = n_called
        m[f"{word}False"] = false
    n_bad, hit, _, _ = flags([(r["actual"], r["pm25"]) for r in scored],
                             POOR)
    m["LivePoorDays"], m["LivePoorHit"] = n_bad, hit

    # --- tests ----------------------------------------------------
    tests = {}
    for path in sorted((ROOT / "code" / "tests").glob("test_*.py")):
        tests[path.name] = len(re.findall(r"^def test_", path.read_text(),
                                          re.MULTILINE))
    m["TestTotal"] = sum(tests.values())
    m["TestFiles"] = len(tests)
    lines = [f"\\texttt{{{k.replace('_', chr(92) + '_')}}} & {v} \\\\"
             for k, v in sorted(tests.items(), key=lambda kv: -kv[1])]
    (DATA / "tests.tex").write_text("\n".join(lines) + "\n")

    # --- numbers.tex ----------------------------------------------
    body = ["% Written by scripts/final_report_figures.py. Do not edit."]
    for k, v in m.items():
        body.append(f"\\newcommand{{\\{k}}}{{{v}}}")
    (DATA / "numbers.tex").write_text("\n".join(body) + "\n")

    charts(runs, rows, models, by_age, scored)
    print(f"wrote {len(m)} figures, 4 tables and 5 charts, "
          f"as of {snapshot}")


def dates(ax):
    """Month ticks, labelled once per year."""
    loc = mdates.AutoDateLocator(minticks=4, maxticks=10)
    ax.xaxis.set_major_locator(loc)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(loc))


def charts(runs, rows, models, by_age, scored):
    # 1. the whole record: observed against the walk-forward forecast
    fig, ax = plt.subplots(figsize=(6.3, 2.6))
    days = [date.fromisoformat(r["date"]) for r in runs]
    for year in (2025, 2026):
        ax.axvspan(date(year, 10, 1), date(year, 11, 30), color=ORANGE,
                   alpha=0.08, lw=0)
    cams = {r["date"]: num(r["cams_pm25"]) for r in rows}
    ax.plot(days, [cams.get(r["date"]) for r in runs], color=ORANGE,
            lw=0.6, alpha=0.6, label="CAMS, uncorrected")
    ax.plot(days, [r["truth"] for r in runs], color=INK, lw=0.9,
            label="Measured")
    ax.plot(days, [r["model"] for r in runs], color=BLUE, lw=0.9,
            label="Pawan, walk-forward")
    ax.set_yscale("log")
    ax.set_ylabel("Daily mean PM$_{2.5}$ (µg/m³)")
    ax.legend(frameon=False, ncol=3, loc="upper left")
    ax.text(date(2025, 10, 3), ax.get_ylim()[0] * 1.15,
            "burning season", color=ORANGE, fontsize=7)
    dates(ax)
    fig.savefig(FIGS / "record.pdf")
    plt.close(fig)

    # 2. how far off CAMS is at this station
    pairs = [(num(r["cams_pm25"]), num(r["obs_pm25"])) for r in rows
             if num(r["cams_pm25"]) and num(r["obs_pm25"])]
    fig, ax = plt.subplots(figsize=(3.1, 3.0))
    ax.scatter([p[1] for p in pairs], [p[0] for p in pairs], s=5,
               color=ORANGE, alpha=0.45, lw=0)
    top = max(max(p) for p in pairs) * 1.05
    ax.plot([1, top], [1, top], color=INK, lw=0.8, ls="--")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Measured (µg/m³)")
    ax.set_ylabel("CAMS forecast (µg/m³)")
    ax.text(0.05, 0.92, "dashed: a perfect forecast", fontsize=7,
            transform=ax.transAxes)
    fig.savefig(FIGS / "cams.pdf")
    plt.close(fig)

    # 3. the leaderboard
    shown = [x for x in models if x["key"] != "raw_cams"]
    fig, ax = plt.subplots(figsize=(6.0, 3.0))
    names = [x["label"] for x in shown][::-1]
    maes = [x["overall"]["mae"] for x in shown][::-1]
    colours = [BLUE if x.get("shipped") else
               ("white" if x["kind"] == "baseline" else GREY)
               for x in shown][::-1]
    ax.barh(names, maes, color=colours, edgecolor=INK, lw=0.6)
    pers = next(x for x in shown if x["key"] == "persistence")
    ax.axvline(pers["overall"]["mae"], color=INK, ls="--", lw=0.8)
    for y, v in enumerate(maes):
        ax.text(v + 0.1, y, f"{v:.2f}", va="center", fontsize=7)
    ax.set_xlabel("Mean absolute error, walk-forward backtest (µg/m³)")
    ax.set_xlim(0, max(maes) * 1.12)
    fig.savefig(FIGS / "leaderboard.pdf")
    plt.close(fig)

    # 4. error against the age of the station reading
    ages = sorted(by_age)
    fig, ax = plt.subplots(figsize=(3.4, 2.5))
    ax.plot(ages, [by_age[a]["persistence_mae"] for a in ages], color=GREY,
            ls="--", marker="o", ms=3, label="Persistence")
    ax.plot(ages, [by_age[a]["mae"] for a in ages], color=BLUE,
            marker="o", ms=3, label="Pawan")
    ax.set_xlabel("Age of the station reading (days)")
    ax.set_ylabel("Mean absolute error (µg/m³)")
    ax.legend(frameon=False)
    fig.savefig(FIGS / "age.pdf")
    plt.close(fig)

    # 5. the live record, with the likely range where there is one
    fig, ax = plt.subplots(figsize=(6.3, 2.4))
    d = [date.fromisoformat(r["date"]) for r in scored]
    ax.plot(d, [r["actual"] for r in scored], color=INK, lw=0, marker="o",
            ms=3, label="Measured")
    ax.plot(d, [r["pm25"] for r in scored], color=BLUE, lw=0, marker="s",
            ms=3, label="Pawan forecast")
    for r, day in zip(scored, d):
        if r.get("interval"):
            ax.plot([day, day], r["interval"], color=BLUE, lw=0.6,
                    alpha=0.5)
    ax.set_ylabel("PM$_{2.5}$ (µg/m³)")
    ax.legend(frameon=False, loc="upper left")
    dates(ax)
    fig.savefig(FIGS / "live.pdf")
    plt.close(fig)


if __name__ == "__main__":
    main()
