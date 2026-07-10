# Weekly Market Dashboard

An automated, self-updating market dashboard focused on **industrial, logistics,
retail, and macro**. Every Monday at 7:00 AM Central a GitHub Action fetches
fresh data, builds a single dark-theme HTML page, publishes it to **GitHub
Pages**, and emails you a "What Changed This Week" summary.

<img width="700" alt="dashboard preview" src="https://via.placeholder.com/700x400/1a1a19/eda100?text=Weekly+Market+Dashboard">

## What's in it

| Section | Contents |
|---------|----------|
| **⚡ What Changed** | Any metric >1σ vs its 12-week average, biggest stock movers, 10Y move >10 bps |
| **Macro Snapshot** | SPY, TLT, US Dollar Index — price, weekly %, YTD %, sparkline |
| **Manufacturing & Macro** | FRED series (10Y, Industrial Production, New Orders, Truck Tonnage, Retail Sales, Empire & Philly Fed) with release dates |
| **Manufacturing PMI** | Scraped ISM headline; falls back to Empire/Philly Fed proxies if the scrape fails |
| **Freight** | Cass Freight Index + AAR weekly rail traffic headlines |
| **Watchlist** | 12 tickers grouped by theme — price, weekly %, YTD %, 52-week range bar, 12-week sparkline |
| **News** | Top 3 Google News headlines per ticker + 5 macro headlines, deduped |

## Architecture

```
market_dashboard/
  config.py           # tickers, FRED series, thresholds, file paths — tweak here
  utils.py            # logging, retry w/ backoff, HTTP session, JSON cache
  fetch_stocks.py     # yfinance equity metrics (3-attempt retry)
  fetch_fred.py       # FRED macro series
  fetch_news.py       # Google News RSS + dedupe
  scrape_pmi.py       # ISM PMI / Cass / AAR best-effort scrapers
  build_dashboard.py  # HTML render + "What Changed" analysis
  notify.py           # Gmail SMTP email
  main.py             # orchestrator: fetch → merge cache → render → email
  selftest.py         # offline render test with synthetic data (no network)
cache/last_values.json  # last-known-good values, committed by the Action
.github/workflows/weekly-dashboard.yml
```

**Resilience by design:** every fetch is wrapped in `try/except`. A failed
section renders "data unavailable this week" instead of crashing, and falls back
to the last cached value (flagged **stale**). yfinance calls retry 3× with
exponential backoff. All failures are logged to the GitHub Actions run summary.

---

## Setup — step by step

You only do steps 1–7 once. After that it runs itself.

### 1. Create the repo

If you're reading this, the code already lives in a repo. If you're starting
fresh, create one on GitHub (`New repository`), then push this folder to it.
The code lives under `market_dashboard/` and the workflow under
`.github/workflows/weekly-dashboard.yml`.

### 2. Get a free FRED API key

1. Go to <https://fred.stlouisfed.org> and create a free account (or sign in).
2. Visit <https://fredaccount.stlouisfed.org/apikeys> → **Request API Key**.
3. Fill in the short form (any description like "personal market dashboard").
4. Copy the 32-character key it gives you — you'll paste it in step 5.

### 3. Create a Gmail App Password

App passwords require 2-Step Verification to be **on** for your Google account.

1. Turn on 2-Step Verification: <https://myaccount.google.com/signinoptions/two-step-verification>.
2. Go to <https://myaccount.google.com/apppasswords>.
3. Name it "Market Dashboard" and click **Create**.
4. Google shows a **16-character password** (like `abcd efgh ijkl mnop`).
   Copy it **without spaces** → `abcdefghijklmnop`. You can't view it again.

> Your normal Gmail password will **not** work for SMTP — you must use an app
> password.

### 4. Enable GitHub Pages

1. In your repo: **Settings → Pages**.
2. Under **Build and deployment → Source**, choose **GitHub Actions**.
   (Not "Deploy from a branch" — this project deploys via the Action.)
3. Save. The site URL will be `https://<your-username>.github.io/<repo-name>/`.

### 5. Add the three GitHub secrets

In your repo: **Settings → Secrets and variables → Actions → New repository
secret**. Add each of these:

| Secret name | Value |
|-------------|-------|
| `FRED_API_KEY` | the 32-char key from step 2 |
| `GMAIL_ADDRESS` | your Gmail address (the sender **and** recipient) |
| `GMAIL_APP_PASSWORD` | the 16-char app password from step 3 (no spaces) |

### 6. (Optional) confirm permissions

The workflow already requests the permissions it needs (`contents: write`,
`pages: write`, `id-token: write`). If your org restricts Actions, make sure
**Settings → Actions → General → Workflow permissions** allows read/write.

### 7. Do a manual test run

Don't wait until Monday to find out if it works.

1. Go to the **Actions** tab → **Weekly Market Dashboard** workflow.
2. Click **Run workflow** (the `workflow_dispatch` button) → **Run workflow**.
3. Watch the run. Open the completed run and read the **Summary** — it lists
   each section as ✅ fresh or ⚠️ stale, plus any failures.
4. Once **deploy** finishes, open your Pages URL from step 4.
5. Check your inbox for the "📊 Weekly Market Dashboard" email.

If a section shows "data unavailable this week," that's the graceful-failure
path doing its job — check the run summary to see which fetch failed and why.

---

## The schedule & Daylight Saving Time

The cron runs at **12:00 UTC every Monday**:

```yaml
schedule:
  - cron: "0 12 * * 1"
```

- **March → early November** (US Central on **CDT**, UTC-5): 12:00 UTC = **7:00 AM Central**. ✅
- **November → March** (US Central on **CST**, UTC-6): 12:00 UTC = **6:00 AM Central**.

GitHub cron has no timezone support, so when Central switches to standard time
in November, **edit the cron to `"0 13 * * 1"`** to keep delivery at 7 AM. Switch
it back to `"0 12 * * 1"` when DST resumes in March.

## Running it locally

```bash
pip install -r market_dashboard/requirements.txt

# Offline render test (no network, no keys) — writes public/index.html + a
# degraded-mode preview you can open in a browser:
python -m market_dashboard.selftest

# Full live run (needs FRED_API_KEY; Gmail vars optional):
export FRED_API_KEY=your_key
export GMAIL_ADDRESS=you@gmail.com          # optional
export GMAIL_APP_PASSWORD=your_app_password  # optional
python -m market_dashboard.main
open public/index.html
```

## Customizing

Almost everything is in `config.py`:

- **Tickers** — edit `WATCHLIST_GROUPS` / `MACRO_TICKERS`.
- **FRED series** — edit `FRED_SERIES`.
- **News topics** — edit `MACRO_NEWS_TOPICS`.
- **Alert thresholds** — `ZSCORE_THRESHOLD`, `RATE_MOVE_BPS_THRESHOLD`, `TOP_MOVERS`.
- **Retry behavior** — `YF_RETRIES`, `YF_RETRY_BACKOFF`.

## Notes & caveats

- **yfinance is unofficial** and occasionally rate-limits or returns gaps. The
  cache + stale-flag design means a bad Yahoo morning shows last week's number,
  not a broken page.
- **Scrapers are best-effort.** ISM/Cass/AAR are public HTML pages with no API;
  if they redesign, the scrape fails gracefully and the dashboard notes it.
- **Not investment advice.** This is a personal information dashboard.
