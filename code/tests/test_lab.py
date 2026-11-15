"""Tests for the model lab.

The lab exists to compare models fairly, so most of these check
fairness: no candidate may learn from a day the real forecast could
not have seen, every candidate is scored on the same days, and the
promotion rule says what it says no matter who is being judged.
"""

import json
import math
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import candidates
import config
import features
import lab

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_features import synthetic


class Spy(candidates.Candidate):
    """Records what each fit was trained on and asked about."""

    key, label, kind = "spy", "Spy", "linear"

    def __init__(self, refit_every=1):
        self.refit_every = refit_every
        self.fits = []

    def fit(self, train):
        record = {"newest": train[-1].day, "asked": []}
        self.fits.append(record)

        def one(sample):
            record["asked"].append(sample.day)
            return 1.0
        return candidates.Fitted(one)


def test_walk_never_learns_from_an_unpublished_day():
    for age in (2, 4):
        spy = Spy()
        lab.walk(spy, features.build(synthetic(90), age=age))
        assert spy.fits
        for fit in spy.fits:
            for day in fit["asked"]:
                assert fit["newest"] <= day - timedelta(days=age)


def test_weekly_refits_still_never_see_the_future():
    """A fit made on Monday answers for the rest of the week, and
    every one of those answers must still be honest."""
    spy = Spy(refit_every=7)
    lab.walk(spy, features.build(synthetic(90), age=2))
    assert len(spy.fits) < 20
    for fit in spy.fits:
        assert len(fit["asked"]) <= 7
        for day in fit["asked"]:
            assert fit["newest"] <= day - timedelta(days=2)


def test_every_standard_library_candidate_predicts():
    rows = synthetic(90)
    for c in candidates.lineup():
        if c.sklearn or isinstance(c, candidates.Ensemble):
            continue
        samples = features.build(rows, extra=c.extra)
        ready = features.usable(samples)
        value = c.fit(ready[:60]).predict(ready[60])
        assert value is not None and value >= 0, c.key


def test_scikit_learn_candidates_predict():
    import pytest

    pytest.importorskip("sklearn")
    ready = features.usable(features.build(synthetic(90)))
    for c in (candidates.RandomForest(), candidates.GradientBoosting(),
              candidates.NeuralNet()):
        got = c.fit(ready[:60]).predict_many(ready[60:63])
        assert len(got) == 3 and all(v >= 0 for v in got), c.key


def test_the_ensemble_is_the_mean_in_log_space():
    got = candidates.Ensemble.combine([10.0, 100.0])
    assert math.isclose(got, math.expm1((math.log1p(10) + math.log1p(100))
                                        / 2))
    assert 10 < got < 55, "a log mean sits below the plain mean"


def test_nearest_days_come_closest_first():
    ready = features.usable(features.build(synthetic(90)))
    target = ready[-1]
    near = candidates.nearest(ready[:-1], target, 5)
    dists = [d for d, _ in near]
    assert dists == sorted(dists)
    assert all(s.day < target.day for _, s in near)


def test_the_smoke_variant_is_left_out_once_it_ships():
    keys = [c.key for c in candidates.lineup(candidates.SMOKE)]
    assert "ridge_smoke" not in keys
    ridge = next(c for c in candidates.lineup(candidates.SMOKE)
                 if c.key == "ridge")
    assert ridge.extra == candidates.SMOKE


def entry(key, calm, burning, robust=None, shippable=True, kind="linear"):
    return {"key": key, "kind": kind, "shippable": shippable,
            "skill": {"calm": calm, "burning": burning},
            "robust": robust or {}}


SHIPPED = {"key": "ridge", "kind": "linear", "shipped": True,
           "skill": {"calm": 0.13, "burning": 0.19}}


def test_a_small_burning_gain_is_not_enough():
    got = lab.verdict(entry("x", 0.13, 0.21), SHIPPED, {})
    assert got == "Not clearly better in burning season"


def test_a_calm_season_cost_is_capped():
    got = lab.verdict(entry("x", 0.09, 0.30), SHIPPED, {})
    assert got == "Costs too much in calm season"


def test_a_blow_up_at_an_older_reading_fails():
    """The case that made the age test necessary."""
    got = lab.verdict(entry("x", 0.13, 0.23, {"2": 0.99, "4": 1.64}),
                      SHIPPED, {})
    assert got == "Breaks down with 4-day-old readings"


def test_passing_the_backtest_still_waits_for_live_days():
    got = lab.verdict(entry("x", 0.13, 0.23, {"2": 0.99, "4": 1.01}),
                      SHIPPED, {"x": {"n": 5, "mae": 1.0,
                                      "shipped_mae": 2.0}})
    assert got.startswith("Passes the backtest; 5 of 20")


def test_only_a_full_pass_is_ready_to_promote():
    live = {"x": {"n": 25, "mae": 7.0, "shipped_mae": 7.5}}
    got = lab.verdict(entry("x", 0.13, 0.23, {"3": 1.02}), SHIPPED, live)
    assert got == "Ready to promote"
    live["x"]["mae"] = 8.0
    got = lab.verdict(entry("x", 0.13, 0.23, {"3": 1.02}), SHIPPED, live)
    assert got == "Passes the backtest, but not live"


def test_benchmarks_and_baselines_are_never_promoted():
    assert lab.verdict(entry("rf", 0.5, 0.5, shippable=False), SHIPPED,
                       {}).startswith("Benchmark")
    assert lab.verdict(entry("p", 0.0, 0.0, kind="baseline"), SHIPPED,
                       {}) == "Baseline"


def test_the_shipped_entry_is_the_real_forecast_only_at_the_same_age():
    """The shadow board's shipped entry is the real forecast, unless
    that forecast was made from an older reading than everyone else
    is being given, which happens on the morning of a merge."""
    rows = synthetic(90)
    today = date(2026, 3, 30)
    lineup = [c for c in candidates.lineup() if not c.sklearn
              and not isinstance(c, candidates.Ensemble)]
    record = {"date": "2026-03-31", "pm25": 999.0,
              "inputs": {"obs_age_days": 2.0}}
    age, got = lab.shadow(rows, lineup, today, record)
    assert age == 2 and got["ridge"] == 999.0
    record["inputs"]["obs_age_days"] = 4.0
    _, got = lab.shadow(rows, lineup, today, record)
    assert got["ridge"] != 999.0


def test_a_shadow_forecast_is_written_once():
    book = {}
    assert lab.freeze(book, "2026-11-04", "2026-11-03", 2, {"ridge": 66.0})
    assert not lab.freeze(book, "2026-11-04", "2026-11-03", 2,
                          {"ridge": 99.0})
    assert book["2026-11-04"]["models"]["ridge"] == 66.0


def test_shadow_outcomes_are_attached_and_scored_on_shared_days():
    book = {}
    lab.freeze(book, "2026-01-20", "2026-01-19", 2,
               {"ridge": 20.0, "analogs": 15.0})
    lab.freeze(book, "2026-01-21", "2026-01-20", 2, {"ridge": 21.0})
    filled = lab.attach(book, features.build(synthetic(30)))
    assert filled == 2
    live = lab.live_scores(book)
    # analogs skipped the 21st: it is scored on the 20th alone, and
    # compared with what the shipped model did on that same day
    assert live["ridge"]["n"] == 2
    assert live["analogs"]["n"] == 1
    assert live["analogs"]["shipped_mae"] == 1.0  # 20 against 19
    assert live["analogs"]["mae"] == 4.0          # 15 against 19


def test_the_lab_board_is_strict_json():
    rows = synthetic(90)
    lineup = [c for c in candidates.lineup() if not c.sklearn]
    board = lab.backtest(rows, lineup)
    text = json.dumps(board, allow_nan=False)
    assert board["models"] and board["by_age"]
    assert board["reference_age"] == config.OBS_REFERENCE_AGE
    assert "NaN" not in text


def test_a_board_older_than_a_week_is_rerun():
    today = date(2026, 11, 10)
    assert lab.stale(None, today)
    assert lab.stale({"backtest_on": "2026-11-03"}, today)
    assert not lab.stale({"backtest_on": "2026-11-05"}, today)
