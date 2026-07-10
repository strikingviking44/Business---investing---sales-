"""Shared helpers: logging, HTTP session, retry, and the JSON cache.

Design goal: every fetch in this project can fail without taking the whole
run down. These helpers make "log it, fall back to cache, keep going" the
path of least resistance.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Callable

import requests

from . import config

# --------------------------------------------------------------------------
# Logging. We keep a running list of failures so main.py can dump them into
# the GitHub Actions step summary at the end of the run.
# --------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("market_dashboard")

FAILURES: list[str] = []


def record_failure(where: str, err: Exception | str) -> None:
    """Log a failure and stash it for the run summary."""
    msg = f"{where}: {err}"
    log.warning("FAILURE  %s", msg)
    FAILURES.append(msg)


def gh_error(msg: str) -> None:
    """Emit a GitHub Actions error annotation (shows red in the run log)."""
    log.error(msg)
    print(f"::error::{msg}", flush=True)


def gh_warning(msg: str) -> None:
    """Emit a GitHub Actions warning annotation (shows yellow in the run log)."""
    log.warning(msg)
    print(f"::warning::{msg}", flush=True)


def mask(secret: str) -> str:
    """Describe a secret for logs without revealing it: length + last 2 chars."""
    if not secret:
        return "<empty>"
    return f"set (len={len(secret)}, ends '…{secret[-2:]}')"


def http_status_of(err: Exception) -> int | None:
    """Best-effort extraction of an HTTP status code from a requests error."""
    resp = getattr(err, "response", None)
    if resp is not None:
        return getattr(resp, "status_code", None)
    return None


def explain_status(code: int | None) -> str:
    """Human hint for common HTTP status codes we care about."""
    return {
        400: "400 Bad Request — usually an invalid/malformed API key",
        401: "401 Unauthorized — bad API key",
        403: "403 Forbidden — blocked or bad key",
        404: "404 Not Found — bad series id or URL",
        429: "429 Too Many Requests — rate limited, back off",
        500: "500 Server Error — upstream problem, retry later",
        503: "503 Service Unavailable — upstream down, retry later",
    }.get(code, f"HTTP {code}" if code else "no HTTP status (network/DNS/timeout)")


def env_diagnostics() -> None:
    """Log which expected environment variables are present (masked).

    Runs once at startup so the Action log makes it obvious when a secret
    (FRED_API_KEY / Gmail creds) never reached the process.
    """
    import os

    log.info("Environment diagnostics:")
    log.info("  FRED_API_KEY:       %s", mask(os.environ.get("FRED_API_KEY", "")))
    log.info("  GMAIL_ADDRESS:      %s",
             os.environ.get("GMAIL_ADDRESS", "") or "<empty>")
    log.info("  GMAIL_APP_PASSWORD: %s", mask(os.environ.get("GMAIL_APP_PASSWORD", "")))
    log.info("  GITHUB_REPOSITORY:  %s", os.environ.get("GITHUB_REPOSITORY", "") or "<empty>")
    if not os.environ.get("FRED_API_KEY", "").strip():
        gh_error(
            "FRED_API_KEY is not set in the environment. The macro/FRED sections "
            "will be empty. Add it under repo Settings → Secrets and variables → "
            "Actions → New repository secret (name must be exactly FRED_API_KEY), "
            "then re-run the workflow."
        )


# --------------------------------------------------------------------------
# HTTP session with a browser-ish UA (some public pages block default UAs).
# --------------------------------------------------------------------------
def http_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": config.USER_AGENT, "Accept-Language": "en-US,en;q=0.9"})
    return s


def retry(fn: Callable[[], Any], attempts: int, backoff: float, where: str) -> Any:
    """Call `fn` up to `attempts` times with exponential backoff.

    Returns the result, or raises the last exception (caller decides what to
    do with it). Every failed attempt is logged.
    """
    last: Exception | None = None
    delay = backoff
    for i in range(1, attempts + 1):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001 - intentional broad catch for flaky IO
            last = e
            log.warning("%s attempt %d/%d failed: %s", where, i, attempts, e)
            if i < attempts:
                time.sleep(delay)
                delay *= 2
    assert last is not None
    raise last


# --------------------------------------------------------------------------
# Cache. A single JSON blob committed by the Action. Structure:
#   {
#     "generated_at": "...",
#     "stocks": {...}, "fred": {...}, "news": {...},
#     "pmi": {...}, "freight": {...}
#   }
# --------------------------------------------------------------------------
def load_cache() -> dict:
    if not os.path.exists(config.CACHE_FILE):
        return {}
    try:
        with open(config.CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:  # noqa: BLE001
        record_failure("load_cache", e)
        return {}


def save_cache(data: dict) -> None:
    os.makedirs(os.path.dirname(config.CACHE_FILE), exist_ok=True)
    try:
        with open(config.CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True, default=str)
        log.info("Cache written to %s", config.CACHE_FILE)
    except Exception as e:  # noqa: BLE001
        record_failure("save_cache", e)


def merge_section(new: dict | None, cached: dict | None) -> tuple[dict, bool]:
    """Merge a freshly-fetched section with its cached copy.

    Returns (data, used_cache). If `new` is falsy we fall back entirely to
    the cached copy and flag it stale. When both exist we prefer new values
    but keep cached entries for any key that failed to refresh.
    """
    if not new:
        if cached:
            return cached, True
        return {}, False
    if not cached:
        return new, False
    merged = dict(cached)
    merged.update(new)
    return merged, False
