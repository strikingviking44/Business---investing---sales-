"""Offline self-test: exercises the render + analysis path with synthetic data.

This does NOT hit the network. It builds a realistic data dict, runs the
"What Changed" analysis and full HTML render, then writes two files to
public/ so the output can be eyeballed:

  public/index.html          — a fully-populated dashboard
  public/index_degraded.html — the all-sections-unavailable degraded mode

Run: python -m market_dashboard.selftest
"""

from __future__ import annotations

import math
import os

from . import build_dashboard, config


def _spark(base: float, n: int = 12, amp: float = 0.05) -> list[float]:
    return [round(base * (1 + amp * math.sin(i / 1.7)), 2) for i in range(n)]


def _mock_data() -> dict:
    stocks = {}
    seeds = {
        "PLD": (112.4, 3.1, -8.2, 42.0), "EGP": (168.9, 1.2, 4.5, 61.0),
        "FR": (52.1, -0.8, 2.1, 55.0), "GXO": (48.7, 6.4, 18.9, 88.0),
        "MANH": (255.3, -2.2, -5.1, 30.0), "MLI": (78.2, 0.5, 11.2, 72.0),
        "VRT": (98.5, 9.8, 41.0, 95.0), "XLI": (138.1, 1.1, 9.4, 80.0),
        "UNP": (241.6, -1.5, 3.2, 48.0), "NSC": (252.9, -3.4, -1.1, 35.0),
        "XRT": (77.4, 2.0, 6.6, 64.0), "SPY": (601.2, 0.9, 14.1, 91.0),
        "TLT": (88.3, -1.9, -4.2, 22.0), "DX-Y.NYB": (104.8, 0.4, 1.1, 58.0),
    }
    for t, (last, wk, ytd, rng) in seeds.items():
        lo = round(last * 0.78, 2)
        hi = round(last * 1.18, 2)
        stocks[t] = {
            "ticker": t, "label": config.TICKER_LABELS.get(t, t), "last": last,
            "weekly_pct": wk, "ytd_pct": ytd, "low_52w": lo, "high_52w": hi,
            "range_pct": rng, "sparkline": _spark(last, 12, 0.04 + abs(wk) / 100),
            "asof": "2026-07-10",
        }

    fred = {
        "DGS10": {"id": "DGS10", "label": "10-Year Treasury", "units": "%",
                  "latest_value": 4.38, "latest_date": "2026-07-09", "prior_value": 4.25,
                  "prior_date": "2026-07-08", "direction": "up", "is_bps": True,
                  "weekly_change_bps": 14.0, "week_ago_date": "2026-07-02",
                  "sparkline": [4.1, 4.12, 4.09, 4.15, 4.2, 4.18, 4.25, 4.22, 4.28, 4.3, 4.25, 4.38]},
        "INDPRO": {"id": "INDPRO", "label": "Industrial Production", "units": "idx",
                   "latest_value": 103.6, "latest_date": "2026-06-15", "prior_value": 103.2,
                   "prior_date": "2026-05-15", "direction": "up", "is_bps": False,
                   "sparkline": [102.1, 102.4, 102.3, 102.6, 102.8, 103.0, 103.1, 103.2, 103.6]},
        "AMTMNO": {"id": "AMTMNO", "label": "Mfg. New Orders", "units": "$M",
                   "latest_value": 586420, "latest_date": "2026-05-28", "prior_value": 590100,
                   "prior_date": "2026-04-28", "direction": "down", "is_bps": False,
                   "sparkline": [582000, 585000, 588000, 591000, 590100, 586420]},
        "TRUCKD11RSA": {"id": "TRUCKD11RSA", "label": "Truck Tonnage", "units": "idx",
                        "latest_value": 114.9, "latest_date": "2026-06-20", "prior_value": 116.1,
                        "prior_date": "2026-05-20", "direction": "down", "is_bps": False,
                        "sparkline": [117.0, 116.8, 116.5, 116.1, 115.5, 114.9]},
        "RSAFS": {"id": "RSAFS", "label": "Retail Sales", "units": "$M",
                  "latest_value": 724800, "latest_date": "2026-06-17", "prior_value": 721300,
                  "prior_date": "2026-05-17", "direction": "up", "is_bps": False,
                  "sparkline": [710000, 713000, 716000, 719000, 721300, 724800]},
        "GACDISA066MSFRBNY": {"id": "GACDISA066MSFRBNY", "label": "Empire State Mfg (NY Fed)",
                              "units": "idx", "latest_value": -8.4, "latest_date": "2026-06-16",
                              "prior_value": -12.2, "prior_date": "2026-05-16", "direction": "up",
                              "is_bps": False, "sparkline": [2.1, -1.0, -4.5, -9.0, -12.2, -8.4]},
        "GACDFSA066MSFRBPHI": {"id": "GACDFSA066MSFRBPHI", "label": "Philly Fed Mfg",
                               "units": "idx", "latest_value": 4.1, "latest_date": "2026-06-19",
                               "prior_value": 1.3, "prior_date": "2026-05-19", "direction": "up",
                               "is_bps": False, "sparkline": [-3.0, -1.5, 0.5, 1.3, 2.0, 4.1]},
    }

    news = {
        "tickers": {
            "VRT": [{"title": "Vertiv raises guidance on AI datacenter cooling demand",
                     "link": "https://example.com/1", "source": "Reuters", "published": "2026-07-08"},
                    {"title": "Analysts lift Vertiv price target ahead of earnings",
                     "link": "https://example.com/2", "source": "Barron's", "published": "2026-07-07"}],
            "GXO": [{"title": "GXO wins major e-commerce fulfillment contract in Europe",
                     "link": "https://example.com/3", "source": "Supply Chain Dive", "published": "2026-07-06"}],
            "UNP": [{"title": "Union Pacific volumes dip on softer coal shipments",
                     "link": "https://example.com/4", "source": "Trains", "published": "2026-07-09"}],
        },
        "macro": [
            {"title": "Fed holds rates steady, signals data-dependent path", "link": "https://example.com/m1",
             "source": "AP", "published": "2026-07-09", "topic": "Fed"},
            {"title": "New tariffs on imported machinery take effect Monday", "link": "https://example.com/m2",
             "source": "Bloomberg", "published": "2026-07-07", "topic": "Tariffs"},
            {"title": "US manufacturing output ticks up for third straight month", "link": "https://example.com/m3",
             "source": "WSJ", "published": "2026-07-08", "topic": "Manufacturing"},
        ],
    }

    pmi = {
        "ism_pmi": {"available": True, "value": 49.2, "period": "June 2026",
                    "expansion": False, "source": config.ISM_PMI_URL},
        "cass": {"available": True,
                 "headline": "Shipments fell 2.8% year over year in June as freight demand stayed soft",
                 "source": config.CASS_FREIGHT_URL},
        "aar": {"available": False, "note": "AAR rail traffic unavailable this week."},
    }

    return {"stocks": stocks, "fred": fred, "news": news, "pmi": pmi}


def main() -> None:
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    # Full dashboard.
    data = _mock_data()
    stale = {"stocks": False, "fred": False, "news": False, "pmi": True}
    html, summary = build_dashboard.build(data, stale, "2026-07-10 12:00 UTC")
    with open(config.OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Wrote {config.OUTPUT_HTML} ({len(html)} bytes)")
    print("\n--- What Changed summary ---")
    print(summary.replace("{dashboard_url}", "https://example.github.io/repo/"))

    # Degraded (everything empty) — must still render a valid page.
    empty = {"stocks": {}, "fred": {}, "news": {}, "pmi": {}}
    stale_all = {k: True for k in empty}
    html2, _ = build_dashboard.build(empty, stale_all, "2026-07-10 12:00 UTC")
    degraded = os.path.join(config.OUTPUT_DIR, "index_degraded.html")
    with open(degraded, "w", encoding="utf-8") as f:
        f.write(html2)
    print(f"\nWrote {degraded} ({len(html2)} bytes)")


if __name__ == "__main__":
    main()
