# Weekly Market Dashboard

An automated, self-updating market dashboard focused on **industrial, logistics,
retail, and macro**. Every Monday at 7:00 AM Central, a GitHub Action fetches
fresh data, builds a single dark-theme HTML page, publishes it to **GitHub
Pages**, and emails a "What Changed This Week" summary.

➡️ **Full documentation and step-by-step setup guide:
[`market_dashboard/README.md`](market_dashboard/README.md)**

## What it does

| Section | Contents |
|---------|----------|
| **⚡ What Changed** | Any metric >1σ vs its 12-week average, biggest stock movers, 10Y move >10 bps |
| **Macro Snapshot** | SPY, TLT, US Dollar Index — price, weekly %, YTD %, sparkline |
| **Manufacturing & Macro** | FRED series (10Y, Industrial Production, New Orders, Truck Tonnage, Retail Sales, Empire & Philly Fed) with release dates |
| **Manufacturing PMI** | Scraped ISM headline; falls back to Empire/Philly Fed proxies if the scrape fails |
| **Freight** | Cass Freight Index + AAR weekly rail traffic headlines |
| **Watchlist** | 12 tickers grouped by theme — price, weekly %, YTD %, 52-week range bar, 12-week sparkline |
| **News** | Top 3 Google News headlines per ticker + 5 macro headlines, deduped |

## Quick start

```bash
pip install -r requirements.txt

# Offline render test (no network, no keys) — writes public/index.html:
python -m market_dashboard.selftest

# Full live run (needs FRED_API_KEY; Gmail vars optional):
export FRED_API_KEY=your_key
python -m market_dashboard.main
```

Runs automatically via GitHub Actions every Monday, and can be triggered manually
from the **Actions** tab (`workflow_dispatch`). See
[`market_dashboard/README.md`](market_dashboard/README.md) for how to add the
required secrets (`FRED_API_KEY`, `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`), enable
GitHub Pages, and do a manual test run.

## Project structure

```
market_dashboard/
  config.py           # tickers, FRED series, thresholds — tweak here
  utils.py            # logging, retry, HTTP session, JSON cache
  fetch_stocks.py     # yfinance equity metrics (3-attempt retry)
  fetch_fred.py       # FRED macro series
  fetch_news.py       # Google News RSS + dedupe
  scrape_pmi.py       # ISM PMI / Cass / AAR best-effort scrapers
  build_dashboard.py  # HTML render + "What Changed" analysis
  notify.py           # Gmail SMTP email
  main.py             # orchestrator
  selftest.py         # offline render test with synthetic data
cache/last_values.json  # last-known-good values, committed by the Action
tests/test_dashboard.py
.github/workflows/weekly-dashboard.yml
```

_Not investment advice._
