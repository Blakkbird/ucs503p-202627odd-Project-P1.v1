"""Characterise the CAMS error: bias, correlation, and how
much a simple rescale removes. Decides whether to frame the
model as correcting CAMS or as forecasting locally."""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "code"))
import config


def mean(xs):
    return sum(xs) / len(xs)


def pearson(xs, ys):
    mx, my = mean(xs), mean(ys)
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    dx = sum((a - mx) ** 2 for a in xs) ** 0.5
    dy = sum((b - my) ** 2 for b in ys) ** 0.5
    return num / (dx * dy) if dx and dy else 0.0


def linfit(xs, ys):
    """Least squares y = a + b*x."""
    mx, my = mean(xs), mean(ys)
    den = sum((a - mx) ** 2 for a in xs)
    b = sum((a - mx) * (c - my) for a, c in zip(xs, ys)) / den if den else 0
    return my - b * mx, b


def mae(pairs):
    return mean([abs(a - b) for a, b in pairs])


def main():
    if not config.DAILY_CSV.exists():
        print("data/daily.csv missing. Run scripts/bootstrap.py first.")
        return 1

    rows = []
    with open(config.DAILY_CSV, newline="") as f:
        for r in csv.DictReader(f):
            if r["obs_pm25"] and r["cams_pm25"]:
                rows.append((r["date"], float(r["obs_pm25"]),
                             float(r["cams_pm25"])))
    rows.sort()
    if len(rows) < 20:
        print(f"only {len(rows)} usable rows, need at least 20")
        return 1

    dates = [d for d, _, _ in rows]
    obs = [o for _, o, _ in rows]
    cams = [c for _, _, c in rows]

    print(f"period : {dates[0]} to {dates[-1]}  ({len(rows)} days)\n")

    print("LEVELS")
    print(f"  observed mean   : {mean(obs):7.1f} ug/m3"
          f"   range {min(obs):.1f} to {max(obs):.1f}")
    print(f"  CAMS mean       : {mean(cams):7.1f} ug/m3"
          f"   range {min(cams):.1f} to {max(cams):.1f}")
    print(f"  ratio CAMS/obs  : {mean(cams) / mean(obs):7.2f}")
    print(f"  signed bias     : {mean(cams) - mean(obs):+7.1f} ug/m3")
    print()

    r = pearson(cams, obs)
    print("SIGNAL")
    print(f"  correlation r   : {r:7.3f}")
    print(f"  r-squared       : {r * r:7.3f}")
    print()

    # How much of the error is removable by a simple rescale?
    a, b = linfit(cams, obs)
    fitted = [a + b * c for c in cams]

    raw_mae = mae(list(zip(obs, cams)))
    fit_mae = mae(list(zip(obs, fitted)))

    pers = [(obs[i], obs[i - 1]) for i in range(1, len(obs))]
    pers_mae = mae(pers)

    clim = mean(obs)
    clim_mae = mae([(o, clim) for o in obs])

    print("ERROR (in-sample, indicative only)")
    print(f"  raw CAMS MAE            : {raw_mae:6.1f}")
    print(f"  CAMS after linear fit   : {fit_mae:6.1f}"
          f"   (obs = {a:.1f} + {b:.3f} * cams)")
    print(f"  climatology MAE         : {clim_mae:6.1f}")
    print(f"  persistence MAE         : {pers_mae:6.1f}")
    print()

    print("=" * 56)
    if abs(r) < 0.25:
        print("VERDICT: CAMS carries little signal at this station.")
        print("Reframe as local forecasting using observation")
        print("history + weather, with CAMS as one weak input.")
    elif fit_mae < pers_mae:
        print("VERDICT: strong bias, and correcting it already")
        print("beats persistence. The correction framing holds.")
    else:
        print("VERDICT: CAMS is badly biased but does carry signal.")
        print("A rescale fixes most of the offset, yet persistence")
        print("is still the harder baseline. Report both, and make")
        print("persistence the primary bar.")
    print("=" * 56)
    return 0


if __name__ == "__main__":
    sys.exit(main())
