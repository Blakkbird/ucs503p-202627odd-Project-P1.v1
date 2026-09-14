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
    page = pages.forecast_page(sample_predictions(), samples)

    assert "# Tomorrow in Patiala" in page
    assert "3" in page and "band" in page.lower()
    assert "<svg" in page


def test_forecast_page_says_so_when_there_is_no_forecast():
    page = pages.forecast_page({"predictions": []},
                                    features.build(synthetic(30)))
    assert "No forecast" in page


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
