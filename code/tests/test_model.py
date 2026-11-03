"""Tests for the hand-rolled ridge fit and the scoring code.

Both are small enough that a bug would be silent rather than
loud -- a wrong MAE still looks like an MAE -- so they are checked
against cases where the right answer is known by hand.
"""

import math
import sys
from datetime import date
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
    runs = evaluate.backtest(samples)

    assert runs, "expected the synthetic set to be long enough"
    for run in runs:
        assert run["trained_to"] < run["day"]


def test_backtest_only_learns_from_published_days():
    """A step may not train on the days between its reading and its
    target: their readings did not exist when it was issued."""
    from datetime import timedelta

    for age in (2, 4):
        runs = evaluate.backtest(features.build(synthetic(90), age=age))
        assert runs
        for run in runs:
            assert run["trained_to"] <= run["day"] - timedelta(days=age)


def test_backtest_declines_when_there_is_too_little_data():
    assert evaluate.backtest(features.build(synthetic(20))) == []


def test_climatology_baseline_is_causal():
    """Day one has no history, so it gets no climatology value."""
    samples = features.build(synthetic(90))
    days = [s.day for s in features.usable(samples)]
    pairs = evaluate.baselines(samples, days)["climatology"]
    assert pairs[0][1] is None or pairs[0][1] < pairs[-1][1]


def test_log_target_round_trips():
    """A fit in log space still predicts in micrograms."""
    x = [[float(a)] for a in range(30)]
    y = [math.expm1(1.0 + 0.08 * a) for a in range(30)]

    model = Ridge(alpha=1e-6, names=["a"], log_target=True).fit(x, y)
    for row, truth in zip(x, y):
        assert abs(model.predict_one(row) - truth) < 1e-3


def test_log_interval_is_asymmetric_and_positive():
    """The band widens upward, and never goes below zero."""
    x = [[float(a)] for a in range(30)]
    y = [math.expm1(1.0 + 0.08 * a) for a in range(30)]
    model = Ridge(alpha=1.0, names=["a"], log_target=True).fit(x, y)

    low, high = model.interval([10.0], sd=0.4)
    point = model.predict_one([10.0])
    assert 0.0 <= low < point < high
    assert (high - point) > (point - low)


def test_model_survives_a_save_and_load(tmp_path):
    """A reloaded model predicts what the fitted one predicted.

    tmp_path rather than NamedTemporaryFile: on Windows a named
    temporary file cannot be opened a second time while the first
    handle is still open, so saving and then loading the same path
    fails there and nowhere else. CI runs on Linux and would never
    have caught it.
    """
    import json

    x = [[float(a), float(a) % 3] for a in range(30)]
    y = [math.expm1(1.0 + 0.05 * a) for a in range(30)]
    fitted = Ridge(alpha=0.5, names=["a", "b"], log_target=True).fit(x, y)

    path = tmp_path / "model.json"
    fitted.save(path)
    again = Ridge.load(path)

    assert again.log_target is True
    assert json.loads(json.dumps(again.to_dict()))["names"] == ["a", "b"]
    for row in x:
        assert abs(again.predict_one(row) - fitted.predict_one(row)) < 1e-9


def test_backtest_file_keeps_one_forecast_per_scored_day(tmp_path):
    import json

    samples = features.build(synthetic(n=80))
    runs = evaluate.backtest(samples)
    out = {"window": {"first": runs[0]["day"].isoformat(),
                      "last": runs[-1]["day"].isoformat()}}
    path = tmp_path / "backtest.json"
    evaluate.write_backtest(out, runs, path)

    blob = json.loads(path.read_text())
    days = [r["date"] for r in blob["runs"]]
    assert len(days) == len(runs) == len(set(days))
    assert days == sorted(days)
    assert all(r["model"] >= 0 for r in blob["runs"])


def test_quantile_interpolates_between_neighbours():
    assert evaluate.quantile([0, 10], 0.5) == 5
    assert evaluate.quantile([3, 1, 2], 0.0) == 1
    assert evaluate.quantile([3, 1, 2], 1.0) == 3
    assert evaluate.quantile([], 0.5) is None


def test_likely_range_holds_the_point_and_leans_up():
    """Equal log offsets either side come out lopsided in
    micrograms, wider above: the shape of a quantity that spikes."""
    cal = {"calm": {"low": -0.3, "high": 0.3, "errors": 100}}
    low, high = evaluate.likely_range(40.0, cal, burning=False)
    assert 0 <= low < 40.0 < high
    assert (high - 40.0) > (40.0 - low)
    assert evaluate.likely_range(40.0, cal, burning=True) is None


def test_coverage_only_sizes_a_range_from_earlier_days():
    """The first MIN_ERRORS days have nothing earlier to size from,
    so they are not counted at all rather than counted as hits."""
    from datetime import timedelta

    start = date(2026, 1, 1)
    runs = [{"day": start + timedelta(days=i), "truth": 20.0,
             "model": 20.0 * (1.1 if i % 2 else 0.9)} for i in range(60)]
    got = evaluate.coverage(runs)
    assert got["overall"]["days"] == 60 - evaluate.MIN_ERRORS
    assert 0 <= got["overall"]["held"] <= got["overall"]["days"]


def test_calibration_falls_back_to_the_whole_year_when_short():
    from datetime import timedelta

    start = date(2026, 1, 1)
    runs = [{"day": start + timedelta(days=i), "truth": 20.0 + i % 5,
             "model": 21.0} for i in range(40)]
    runs.append({"day": date(2026, 10, 2), "truth": 90.0, "model": 60.0})
    cal = evaluate.calibrate(runs)
    assert cal["burning"]["errors"] == len(runs)  # borrowed the year
    assert cal["calm"]["errors"] == 40
