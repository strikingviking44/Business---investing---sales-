"""Central configuration for the weekly market dashboard.

Everything that a human might want to tweak (which tickers to track, which
FRED series to pull, file locations, colors) lives here so the fetch/build
modules stay generic.
"""

from __future__ import annotations

import os

# --------------------------------------------------------------------------
# Watchlist — grouped so the dashboard can render sections in a sensible order.
# Each entry: (ticker, human label). Groups are ordered dicts.
# --------------------------------------------------------------------------
WATCHLIST_GROUPS: dict[str, list[tuple[str, str]]] = {
    "Industrial Real Estate": [
        ("PLD", "Prologis"),
        ("EGP", "EastGroup Properties"),
        ("FR", "First Industrial Realty"),
    ],
    "Logistics / Supply Chain": [
        ("GXO", "GXO Logistics"),
        ("MANH", "Manhattan Associates"),
    ],
    "Industrials / Manufacturing": [
        ("MLI", "Mueller Industries"),
        ("VRT", "Vertiv Holdings"),
        ("XLI", "Industrial Select Sector SPDR"),
    ],
    "Rail": [
        ("UNP", "Union Pacific"),
        ("NSC", "Norfolk Southern"),
    ],
    "Retail": [
        ("XRT", "SPDR S&P Retail ETF"),
    ],
}

# Macro row is displayed separately from the watchlist.
MACRO_TICKERS: list[tuple[str, str]] = [
    ("SPY", "S&P 500 ETF"),
    ("TLT", "20+ Year Treasury ETF"),
    ("DX-Y.NYB", "US Dollar Index"),
]

# Flat list of every equity ticker we need to fetch.
ALL_TICKERS: list[str] = [
    t for group in WATCHLIST_GROUPS.values() for (t, _label) in group
] + [t for (t, _label) in MACRO_TICKERS]

TICKER_LABELS: dict[str, str] = {
    t: label
    for group in WATCHLIST_GROUPS.values()
    for (t, label) in group
}
TICKER_LABELS.update({t: label for (t, label) in MACRO_TICKERS})

# --------------------------------------------------------------------------
# FRED series. `bps=True` means we express the weekly change in basis points
# (used for rates). `sparkline_months` controls how much history we chart.
# `units` is a short display suffix.
# --------------------------------------------------------------------------
FRED_SERIES: list[dict] = [
    {
        "id": "DGS10",
        "label": "10-Year Treasury",
        "units": "%",
        "bps": True,
        "sparkline_months": 6,
    },
    {
        "id": "INDPRO",
        "label": "Industrial Production",
        "units": "idx",
        "bps": False,
        "sparkline_months": 12,
    },
    {
        "id": "AMTMNO",
        "label": "Mfg. New Orders",
        "units": "$M",
        "bps": False,
        "sparkline_months": 12,
    },
    {
        "id": "TRUCKD11RSA",
        "label": "Truck Tonnage",
        "units": "idx",
        "bps": False,
        "sparkline_months": 12,
    },
    {
        "id": "RSAFS",
        "label": "Retail Sales",
        "units": "$M",
        "bps": False,
        "sparkline_months": 12,
    },
    {
        "id": "GACDISA066MSFRBNY",
        "label": "Empire State Mfg (NY Fed)",
        "units": "idx",
        "bps": False,
        "sparkline_months": 12,
    },
    {
        "id": "GACDFSA066MSFRBPHI",
        "label": "Philly Fed Mfg",
        "units": "idx",
        "bps": False,
        "sparkline_months": 12,
    },
]

# Series used as ISM PMI proxies when the ISM scrape fails.
PMI_PROXY_SERIES = ["GACDISA066MSFRBNY", "GACDFSA066MSFRBPHI"]

# --------------------------------------------------------------------------
# News — Google News RSS. Macro topics get their own searches.
# --------------------------------------------------------------------------
NEWS_HEADLINES_PER_TICKER = 3
NEWS_LOOKBACK_DAYS = 7
MACRO_NEWS_TOPICS: list[tuple[str, str]] = [
    ("Federal Reserve interest rates", "Fed"),
    ("US tariffs trade", "Tariffs"),
    ("US manufacturing PMI", "Manufacturing"),
    ("freight trucking rail volumes", "Freight"),
    ("industrial real estate warehouse demand", "Industrial RE"),
]
MACRO_NEWS_TOTAL = 5

# --------------------------------------------------------------------------
# Scrape targets (best-effort, graceful failure).
# --------------------------------------------------------------------------
ISM_PMI_URL = "https://www.ismworld.org/supply-management-news-and-reports/reports/ism-report-on-business/pmi/"
CASS_FREIGHT_URL = "https://www.cassinfo.com/freight-audit-payment/cass-transportation-indexes/cass-freight-index"
AAR_RAIL_URL = "https://www.aar.org/data-center/rail-traffic-data/"

# --------------------------------------------------------------------------
# Files / environment.
# --------------------------------------------------------------------------
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_FILE = os.path.join(_ROOT, "cache", "last_values.json")
OUTPUT_DIR = os.path.join(_ROOT, "public")
OUTPUT_HTML = os.path.join(OUTPUT_DIR, "index.html")

FRED_API_KEY = os.environ.get("FRED_API_KEY", "")
FRED_BASE = "https://api.stlouisfed.org/fred"

# Retry / timeout knobs.
YF_RETRIES = 3
YF_RETRY_BACKOFF = 2.0  # seconds, doubles each attempt
HTTP_TIMEOUT = 20
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

# "What changed" thresholds.
ZSCORE_THRESHOLD = 1.0        # std devs vs 12-week average
RATE_MOVE_BPS_THRESHOLD = 10  # 10Y move in bps
TOP_MOVERS = 3
