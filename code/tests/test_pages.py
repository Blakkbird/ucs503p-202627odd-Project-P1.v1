"""Tests for the page generator.

A broken page is not as serious as a broken model, but it is more
visible, and it fails in a way nobody notices until somebody opens
the site. These check the two things that would actually go wrong:
malformed SVG when the record is thin, and a page that quietly
renders with no numbers in it.
"""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import features
import pages

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_features import synthetic


def sample_predictions(n=6):
    start = date(2026, 9, 1)
    records = []
    for i in range(n):
        day = start + timedelta(days=i)
        records.append({
            "date": day.isoformat(),
            "issued": (day - timedelta(days=1)).isoformat(),
            "pm25": 20.0 + i,
            "band": "Good",
            "actual": 22.0 + i if i < 3 else None,
            "error": -2.0 if i < 3 else None,
            "band_hit": True if i < 3 else None,
            "interval": [10.0 + i, 34.0 + i],
        })
    return {"generated_at": "2026-09-13T08:00:00+05:30",
            "predictions": records}


def test_chart_survives_an_empty_record():
    assert "Nothing on record" in pages.chart([], [])


def test_chart_survives_a_single_point():
    """One day either side must not produce a degenerate scale."""
    svg = pages.chart([(date(2026, 9, 1), 20.0)],
                           [(date(2026, 9, 1), 18.0, 8.0, 28.0)])
    assert svg.startswith("<svg")
    assert svg.count("<svg") == svg.count("</svg>") == 1
    assert "nan" not in svg.lower()


def test_chart_is_well_formed():
    from xml.etree import ElementTree

    blob = sample_predictions()
    observed = [(date.fromisoformat(r["date"]), r["actual"])
                for r in blob["predictions"] if r["actual"] is not None]
    drawn = [(date.fromisoformat(r["date"]), r["pm25"],
              r["interval"][0], r["interval"][1])
             for r in blob["predictions"]]

    svg = pages.chart(observed, drawn)
    root = ElementTree.fromstring(svg)  # raises if the SVG is malformed
    assert root.tag.endswith("svg")


def test_forecast_page_reports_the_live_record():
    samples = features.build(synthetic(30))
    page = pages.forecast_page(sample_predictions(), samples,
                               today=date(2026, 9, 4))

    assert "# Tomorrow in Patiala" in page
    assert "3" in page and "band" in page.lower()
    assert "<svg" in page


def test_forecast_page_says_so_when_there_is_no_forecast():
    page = pages.forecast_page({"predictions": []},
                               features.build(synthetic(30)),
                               today=date(2026, 9, 4))
    assert "No forecast" in page


def test_a_stale_forecast_is_not_shown_as_tomorrows():
    """Records run to 6 September. On the 10th, tomorrow is the
    11th, and the page must not dress the 6th up as it."""
    blob = sample_predictions()
    blob["status"] = {"target": "2026-09-11", "issued": False,
                      "reason": "the station has not published a "
                                "usable reading recent enough to work from"}
    page = pages.forecast_page(blob, features.build(synthetic(30)),
                               today=date(2026, 9, 10))
    assert "No forecast" in page
    assert "Friday 11 September" in page
    assert "station has not published" in page
    assert "last forecast on record was for Sunday 06 September" in page


def test_a_reason_for_some_other_day_is_not_reused():
    blob = sample_predictions()
    blob["status"] = {"target": "2026-09-08", "issued": False,
                      "reason": "something that happened on the 7th"}
    page = pages.forecast_page(blob, features.build(synthetic(30)),
                               today=date(2026, 9, 10))
    assert "happened on the 7th" not in page
    assert "has not issued one yet" in page


def test_tomorrows_forecast_is_shown_when_it_exists():
    page = pages.forecast_page(sample_predictions(),
                               features.build(synthetic(30)),
                               today=date(2026, 9, 5))
    assert "No forecast" not in page
    assert "Sunday 06 September" in page


def test_results_page_reports_both_baselines():
    metrics = {
        "window": {"first": "2026-07-27", "last": "2026-09-11"},
        "min_train": 40,
        "overall": {
            "model": {"n": 40, "mae": 3.29, "rmse": 4.26, "bias": 0.09,
                      "band_hit_rate": 1.0},
            "persistence": {"n": 39, "mae": 3.48, "rmse": 4.26,
                            "bias": -0.65, "band_hit_rate": 1.0},
            "persistence_operational": {"n": 40, "mae": 4.60, "rmse": 5.89,
                                        "bias": -1.54, "band_hit_rate": 1.0},
        },
        "skill": {"operational": 0.283, "textbook": 0.052},
    }
    model = {"names": ["cams_log", "temp"], "coef": [0.14, 0.10]}
    page = pages.results_page(metrics, model)

    # Both baselines have to appear. Reporting only the flattering
    # one is the failure this page exists to prevent.
    assert "operational persistence" in page
    assert "textbook persistence" in page
    assert "28.3% better" in page
    assert "cams_log" in page


def test_results_page_survives_a_missing_backtest():
    assert "No backtest" in pages.results_page(None, None)


def metrics_with(by_season, by_provenance=None, counts=None):
    block = {"n": 50, "mae": 4.0, "rmse": 5.0, "bias": 0.1,
             "band_hit_rate": 0.9}
    return {
        "window": {"first": "2025-04-01", "last": "2026-10-05"},
        "min_train": 40,
        "overall": {"model": block, "persistence_operational": block},
        "skill": {"operational": 0.3, "textbook": 0.02},
        "by_season": by_season,
        "by_provenance": by_provenance or {},
        "counts": counts or {},
    }


def scores(model_mae, ref_mae, n=50):
    def block(mae):
        return {"n": n, "mae": mae, "rmse": mae, "bias": 0.0,
                "band_hit_rate": 0.9}
    return {"model": block(model_mae),
            "persistence_operational": block(ref_mae)}


def test_results_page_admits_burning_has_not_been_scored():
    page = pages.results_page(
        metrics_with({"calm": scores(4.0, 6.0)}), None)
    assert "has never fired" in page
    assert "not yet scored" in page


def test_results_page_stops_saying_never_fired_once_it_has():
    page = pages.results_page(metrics_with(
        {"calm": scores(4.0, 6.0), "burning": scores(40.0, 55.0, n=48)},
        counts={"burning_backfilled": 44, "burning_live": 4}), None)
    assert "has never fired" not in page
    assert "48 burning-season days" in page
    assert "44 read back from archives and 4 recorded live" in page


def test_season_table_judges_each_target_separately():
    """Calm beats its 10% target here, burning misses its 20%."""
    page = pages.results_page(metrics_with(
        {"calm": scores(4.0, 6.0), "burning": scores(50.0, 55.0)}), None)
    assert "+33.3% | 10%, met" in page
    assert "+9.1% | 20%, not met" in page


def test_live_only_line_appears_when_there_are_live_days():
    page = pages.results_page(metrics_with(
        {"calm": scores(4.0, 6.0)},
        by_provenance={"live": scores(4.0, 7.4, n=43)}), None)
    assert "43" in page and "recorded live" in page


def test_live_only_line_is_skipped_without_live_days():
    page = pages.results_page(metrics_with({"calm": scores(4.0, 6.0)}),
                              None)
    assert "recorded live rather than" not in page


def test_one_burning_day_reads_as_one_day():
    page = pages.results_page(metrics_with(
        {"calm": scores(4.0, 6.0), "burning": scores(12.6, 15.2, n=1)},
        counts={"burning_backfilled": 0, "burning_live": 1}), None)
    assert "1 burning-season day is scored" in page
