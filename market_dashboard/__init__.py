"""Weekly market dashboard package.

Modules:
  config           — tickers, FRED series, thresholds, file paths
  utils            — logging, retry, HTTP session, JSON cache
  fetch_stocks     — yfinance equity metrics (retry-wrapped)
  fetch_fred       — FRED macro series
  fetch_news       — Google News RSS headlines
  scrape_pmi       — ISM PMI / Cass / AAR best-effort scrapers
  build_dashboard  — HTML render + "What Changed" analysis
  notify           — Gmail SMTP email
  main             — orchestrator (run with `python -m market_dashboard.main`)
"""

__version__ = "1.0.0"
