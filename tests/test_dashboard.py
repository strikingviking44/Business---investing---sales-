"""Weekly Market Dashboard tests (offline — no network).

Run: python -m pytest tests/test_dashboard.py -v
"""

import os
import sys

# Make the repo root importable so `market_dashboard` resolves as a package.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from market_dashboard import build_dashboard, config
from market_dashboard.fetch_news import _dedupe, _similar, _tokens
from market_dashboard.selftest import _mock_data


def test_config_ticker_coverage():
    # Every watchlist + macro ticker has a label and appears in ALL_TICKERS.
    assert "PLD" in config.ALL_TICKERS
    assert "DX-Y.NYB" in config.ALL_TICKERS
    for t in config.ALL_TICKERS:
        assert t in config.TICKER_LABELS


def test_sparkline_svg_handles_empty():
    assert "svg" in build_dashboard.sparkline_svg([])
    assert "svg" in build_dashboard.sparkline_svg([1.0])  # too few points
    svg = build_dashboard.sparkline_svg([1, 2, 3, 4])
    assert "polyline" in svg


def test_range_bar_clamps():
    # Out-of-range percentages must not throw and stay within the bar.
    assert "svg" in build_dashboard.range_bar(150, 10, 20)
    assert "—" in build_dashboard.range_bar(None, None, None)


def test_full_render_produces_html():
    data = _mock_data()
    stale = {"stocks": False, "fred": False, "news": False, "pmi": True}
    html, summary = build_dashboard.build(data, stale, "2026-07-10 12:00 UTC")
    assert "<!DOCTYPE html>" in html
    assert "What Changed This Week" in html
    assert "Watchlist" in html
    assert "Macro Snapshot" in html
    # PMI headline from the mock should render.
    assert "49.2" in html
    # Summary references the dashboard link placeholder.
    assert "{dashboard_url}" in summary


def test_degraded_render_never_crashes():
    empty = {"stocks": {}, "fred": {}, "news": {}, "pmi": {}}
    stale = {k: True for k in empty}
    html, _ = build_dashboard.build(empty, stale, "2026-07-10 12:00 UTC")
    assert "<!DOCTYPE html>" in html
    assert "unavailable" in html.lower()


def test_what_changed_flags_big_moves():
    data = _mock_data()
    changes = build_dashboard.analyze_changes(data)
    texts = " ".join(c["text"] for c in changes)
    # 10Y moved +14bps in the mock (> 10bps threshold).
    assert "10-Year Treasury" in texts
    # VRT +9.8% is the biggest mover.
    assert "VRT" in texts


def test_news_dedupe_collapses_similar_headlines():
    # Same wire story picked up by multiple outlets — near-identical wording.
    items = [
        {"title": "Vertiv raises full-year guidance on datacenter cooling demand"},
        {"title": "Vertiv raises full year guidance on datacenter cooling demand"},  # near-dup
        {"title": "Union Pacific volumes dip on softer coal shipments"},
    ]
    kept = _dedupe(items)
    # The two Vertiv headlines collapse to one; Union Pacific stays.
    assert len(kept) == 2


def test_similarity_heuristic():
    a = _tokens("Vertiv raises full-year guidance on datacenter cooling demand")
    b = _tokens("Vertiv raises full year guidance on datacenter cooling demand")
    assert _similar(a, b)
    c = _tokens("Union Pacific volumes dip on softer coal shipments")
    assert not _similar(a, c)
