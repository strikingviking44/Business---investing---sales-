"""Fetch equity data via yfinance.

For each ticker we compute:
  - last price
  - weekly % change (vs ~5 trading days ago)
  - YTD %
  - 52-week high/low and where the current price sits within that range
  - a 12-week sparkline (weekly closes)

yfinance is an unofficial scraper of Yahoo Finance and is flaky, so every
download is wrapped in retry(). A single ticker failing never aborts the run;
it just gets omitted (and main.py will fall back to the cached value).
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from . import config
from .utils import gh_error, gh_warning, log, record_failure, retry


def _safe_float(x: Any) -> float | None:
    try:
        if x is None:
            return None
        f = float(x)
        if f != f:  # NaN check
            return None
        return f
    except (TypeError, ValueError):
        return None


def _weekly_closes(closes, n: int = 12) -> list[float]:
    """Resample a daily close series to weekly (Friday) and take last n points."""
    try:
        weekly = closes.resample("W-FRI").last().dropna()
        pts = [round(float(v), 2) for v in weekly.tail(n).tolist()]
        return pts
    except Exception:  # noqa: BLE001
        # Fall back to a simple decimation of daily closes.
        vals = [round(float(v), 2) for v in closes.dropna().tolist()]
        return vals[-n:]


def _compute_one(ticker: str, hist) -> dict | None:
    """Turn a yfinance history DataFrame into our metrics dict."""
    if hist is None or hist.empty or "Close" not in hist:
        return None
    closes = hist["Close"].dropna()
    if closes.empty:
        return None

    last = _safe_float(closes.iloc[-1])
    if last is None:
        return None

    # Weekly change: compare to close ~5 trading days ago.
    week_ago = _safe_float(closes.iloc[-6]) if len(closes) >= 6 else _safe_float(closes.iloc[0])
    weekly_pct = ((last - week_ago) / week_ago * 100) if week_ago else None

    # YTD: first close on/after Jan 1 of the current year.
    ytd_pct = None
    try:
        year = closes.index[-1].year
        jan1 = dt.datetime(year, 1, 1)
        ytd_series = closes[closes.index >= jan1.strftime("%Y-%m-%d")]
        if not ytd_series.empty:
            start = _safe_float(ytd_series.iloc[0])
            if start:
                ytd_pct = (last - start) / start * 100
    except Exception:  # noqa: BLE001
        ytd_pct = None

    # 52-week range from the trailing ~252 trading days.
    trailing = closes.tail(252)
    hi = _safe_float(trailing.max())
    lo = _safe_float(trailing.min())
    range_pct = None
    if hi is not None and lo is not None and hi > lo:
        range_pct = (last - lo) / (hi - lo) * 100  # 0 = at low, 100 = at high

    return {
        "ticker": ticker,
        "label": config.TICKER_LABELS.get(ticker, ticker),
        "last": round(last, 2),
        "weekly_pct": round(weekly_pct, 2) if weekly_pct is not None else None,
        "ytd_pct": round(ytd_pct, 2) if ytd_pct is not None else None,
        "low_52w": round(lo, 2) if lo is not None else None,
        "high_52w": round(hi, 2) if hi is not None else None,
        "range_pct": round(range_pct, 1) if range_pct is not None else None,
        "sparkline": _weekly_closes(closes, 12),
        "asof": closes.index[-1].strftime("%Y-%m-%d"),
    }


def fetch_stocks() -> dict[str, dict]:
    """Return {ticker: metrics}. Missing/failed tickers are simply absent."""
    try:
        import yfinance as yf
    except Exception as e:  # noqa: BLE001
        record_failure("fetch_stocks/import", e)
        return {}

    results: dict[str, dict] = {}

    def _download() -> Any:
        # One batched request for all tickers; ~14 months for 52w + YTD math.
        return yf.download(
            tickers=config.ALL_TICKERS,
            period="14mo",
            interval="1d",
            group_by="ticker",
            auto_adjust=True,
            threads=True,
            progress=False,
        )

    data = None
    try:
        data = retry(_download, config.YF_RETRIES, config.YF_RETRY_BACKOFF, "yfinance.download")
    except Exception as e:  # noqa: BLE001
        record_failure("fetch_stocks/batch", e)
        data = None

    for ticker in config.ALL_TICKERS:
        try:
            hist = None
            if data is not None and hasattr(data, "columns"):
                # Batched frame is multi-indexed by ticker when >1 symbol.
                try:
                    hist = data[ticker]
                except Exception:  # noqa: BLE001
                    hist = None
            if hist is None or getattr(hist, "empty", True):
                # Per-ticker fallback with its own retry.
                def _one(tk=ticker):
                    import yfinance as yf  # local import keeps closure clean
                    return yf.Ticker(tk).history(period="14mo", interval="1d", auto_adjust=True)

                hist = retry(_one, config.YF_RETRIES, config.YF_RETRY_BACKOFF, f"yfinance[{ticker}]")

            metrics = _compute_one(ticker, hist)
            if metrics:
                results[ticker] = metrics
                log.info("stock %-10s last=%s wk=%s%%", ticker, metrics["last"], metrics["weekly_pct"])
            else:
                record_failure(f"fetch_stocks[{ticker}]", "no usable price data")
        except Exception as e:  # noqa: BLE001
            record_failure(f"fetch_stocks[{ticker}]", e)

    got, total = len(results), len(config.ALL_TICKERS)
    log.info("fetch_stocks: %d/%d tickers returned data", got, total)
    if got == 0:
        gh_error(
            "fetch_stocks: 0 tickers returned data — yfinance/Yahoo is blocking or "
            "down (no API key involved). Usually transient; re-run in a bit."
        )
    elif got < total:
        gh_warning(f"fetch_stocks: only {got}/{total} tickers returned data (rest stale/missing).")

    return results


if __name__ == "__main__":
    import json

    print(json.dumps(fetch_stocks(), indent=2, default=str))
