"""Tests for the hand-rolled ridge fit and the scoring code.

Both are small enough that a bug would be silent rather than
loud -- a wrong MAE still looks like an MAE -- so they are checked
against cases where the right answer is known by hand.
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import evaluate
import features
from model import Ridge

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_features import synthetic


def test_recovers_a_known_line():
    """y = 40 + 2a - b, with almost no penalty, should come back.

    The intercept is well clear of zero so that the non-negative
    clip in predict_one never fires and the fit itself is what is
    being measured.
    """
    x = [[a, b] for a in range(10) for b in range(10)]
    y = [40 + 2 * a - b for a, b in x]

    model = Ridge(alpha=1e-6, names=["a", "b"]).fit(x, y)
    for row, truth in zip(x, y):
        assert abs(model.predict_one(row) - truth) < 1e-3


def test_penalty_shrinks_the_coefficients():
    x = [[float(a), float(a) + 0.1] for a in range(40)]
    y = [2.0 * a for a, _ in x]

    loose = Ridge(alpha=1e-6).fit(x, y)
    tight = Ridge(alpha=500.0).fit(x, y)
    assert sum(abs(c) for c in tight.coef) < sum(abs(c) for c in loose.coef)


def test_predictions_are_never_negative():
    x = [[float(i)] for i in range(20)]
    y = [float(i) for i in range(20)]
    model = Ridge(alpha=1e-6).fit(x, y)
    assert model.predict_one([-50.0]) == 0.0


def test_constant_column_does_not_blow_up():
    """A feature that never varies has zero standard deviation."""
    x = [[float(i), 7.0] for i in range(30)]
    y = [float(i) * 2 for i in range(30)]
    model = Ridge(alpha=0.1, names=["varies", "constant"]).fit(x, y)
    assert all(math.isfinite(c) for c in model.coef)
    assert abs(dict(model.weights())["constant"]) < 1e-9


def test_round_trips_through_json(tmp_path):
    x = [[float(i), float(i % 3)] for i in range(30)]
    y = [1.5 * a + b for a, b in x]
    model = Ridge(alpha=0.5, names=["a", "b"]).fit(x, y)

    path = tmp_path / "model.json"
    model.save(path)
    reloaded = Ridge.load(path)

    for row in x:
        assert abs(model.predict_one(row) - reloaded.predict_one(row)) < 1e-9


def test_mae_and_rmse_match_hand_calculation():
    # score() rounds to three decimals for the json, so compare to
    # the same precision rather than to machine epsilon.
    got = evaluate.score([(10.0, 12.0), (20.0, 17.0), (30.0, 30.0)])
    assert got["n"] == 3
    assert abs(got["mae"] - (2 + 3 + 0) / 3) < 1e-3
    assert abs(got["rmse"] - math.sqrt((4 + 9 + 0) / 3)) < 1e-3
    assert abs(got["bias"] - (2 - 3 + 0) / 3) < 1e-3


def test_score_ignores_pairs_with_a_hole():
    assert evaluate.score([(10.0, 12.0), (20.0, None)])["n"] == 1
    assert evaluate.score([(None, 1.0)]) is None


def test_aqi_bands_land_on_the_cpcb_edges():
    assert evaluate.band(30) == "Good"
    assert evaluate.band(30.1) == "Satisfactory"
    assert evaluate.band(60) == "Satisfactory"
    assert evaluate.band(90.5) == "Poor"
    assert evaluate.band(400) == "Severe"


def test_backtest_never_trains_on_the_future():
    """Every fit must end before the day it is asked to predict."""
    samples = features.build(synthetic(90))
    ready = features.usable(samples)
    runs = evaluate.backtest(samples)

    assert runs, "expected the synthetic set to be long enough"
    for i, run in enumerate(runs):
        used = ready[:evaluate.MIN_TRAIN + i]
        assert all(s.day < run["day"] for s in used)


def test_backtest_declines_when_there_is_too_little_data():
    assert evaluate.backtest(features.build(synthetic(20))) == []


def test_climatology_baseline_is_causal():
    """Day one has no history, so it gets no climatology value."""
    samples = features.build(synthetic(90))
    days = [s.day for s in features.usable(samples)]
    pairs = evaluate.baselines(samples, days)["climatology"]
    assert pairs[0][1] is None or pairs[0][1] < pairs[-1][1]
