"""Backtest a few candidate models side by side.

Nothing here changes the model the daily job ships. It answers one
question before anything is adopted: does a change earn its place
on burning-season days, without costing more on calm ones than it
gains? Every candidate goes through the same walk-forward backtest
evaluate.py uses, on the same days, and is scored against the same
operational persistence.

    python scripts/compare_models.py

Worth deciding the bar before looking at the table, not after.
Something like: adopt a candidate only if its burning-season skill
is clearly better than the current model's, and its calm-season
skill is no more than a point or two worse. With one season of
burning days, a gain of a percent or two is noise.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))

import config
import evaluate
import features

# (label, extra interactions, fit burning days on burning days only)
CANDIDATES = [
    ("current", (), False),
    ("+ smoke transport", ("burn_fire", "burn_wind_u"), False),
    ("+ season trust", ("burn_obs", "burn_cams"), False),
    ("+ all four", ("burn_fire", "burn_wind_u", "burn_obs",
                    "burn_cams"), False),
    ("separate burning fit", (), True),
]


def walk(samples, separate=False):
    """Walk-forward predictions, as [(sample, prediction)].

    With `separate`, a burning-season day is predicted by a model
    fitted on burning-season days alone, once there are enough of
    them; until then it falls back to the full history, the same
    as the current model.
    """
    ready = features.usable(samples)
    out = []
    for i in range(evaluate.MIN_TRAIN, len(ready)):
        train, target = ready[:i], ready[i]
        if separate and target.burning:
            same = [s for s in train if s.burning]
            if len(same) >= evaluate.MIN_TRAIN:
                train = same
        try:
            model = evaluate.fit(train)
        except ValueError:
            continue
        out.append((target, model.predict_one(target.x)))
    return out


def skill(pairs):
    """(n, model MAE, persistence MAE, skill) on days with both."""
    pairs = [(s, p) for s, p in pairs if s.persistence_op is not None]
    if not pairs:
        return None
    n = len(pairs)
    model = sum(abs(p - s.y) for s, p in pairs) / n
    ref = sum(abs(s.persistence_op - s.y) for s, _ in pairs) / n
    return n, model, ref, (ref - model) / ref if ref else None


def cell(got):
    if got is None:
        return f"{'-':>22s}"
    n, model, _, gain = got
    return f"{n:4d} {model:7.2f} {gain * 100:+8.1f}%"


def main():
    print("Walk-forward backtest, skill against operational persistence")
    print("targets: 10% calm, 20% burning\n")

    head = (f"{'candidate':24s}{'calm  n    MAE    skill':>24s}"
            f"{'burning n    MAE    skill':>26s}"
            f"{'live  n    MAE    skill':>26s}")
    print(head)
    print("-" * len(head))

    days = None
    for label, extra, separate in CANDIDATES:
        samples = features.build(use_weather=True, extra=extra)
        runs = walk(samples, separate)

        # Every candidate has to be scored on the same days, or the
        # table compares different exams. Interactions are built
        # from columns already in the row, so this should always
        # hold; it is checked rather than assumed.
        scored = [s.day for s, _ in runs]
        if days is None:
            days = scored
        elif scored != days:
            print(f"{label}: scored on different days, skipped")
            continue

        calm = [(s, p) for s, p in runs if not s.burning]
        burn = [(s, p) for s, p in runs if s.burning]
        live = [(s, p) for s, p in runs if s.live]
        print(f"{label:24s}  {cell(skill(calm))}  {cell(skill(burn))}"
              f"  {cell(skill(live))}")

    burning_days = sum(1 for d in (days or [])
                       if d.month in config.BURNING_MONTHS)
    if burning_days < 20:
        print(f"\nonly {burning_days} burning-season days scored. Run the "
              "Extend history workflow first; until then the burning "
              "column cannot tell these apart.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
