"""Orchestrator — run with `python -m market_dashboard.main`.

Flow:
  1. Load the last-known-good cache.
  2. Fetch every section, each guarded so one failure can't abort the run.
  3. Merge fresh data over cache; anything that failed to refresh is flagged
     stale and keeps its last known value.
  4. Persist the merged cache (the Action commits it).
  5. Render public/index.html and a plain-text "What Changed" summary.
  6. Write a run report to the GitHub Actions step summary.
  7. Email the summary (if Gmail creds are present).

The process exits 0 even when individual fetches fail — a partially-stale
dashboard is the intended degraded mode, not an error.
"""

from __future__ import annotations

import datetime as dt
import os

from . import build_dashboard, config
from .fetch_fred import fetch_fred
from .fetch_news import fetch_news
from .fetch_stocks import fetch_stocks
from .notify import send_email, summary_to_html
from .scrape_pmi import scrape_all
from .utils import FAILURES, load_cache, log, merge_section, record_failure, save_cache


def _dashboard_url() -> str:
    """Best-effort GitHub Pages URL from the Action environment."""
    explicit = os.environ.get("DASHBOARD_URL", "").strip()
    if explicit:
        return explicit
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()  # "owner/name"
    if "/" in repo:
        owner, name = repo.split("/", 1)
        return f"https://{owner.lower()}.github.io/{name}/"
    return "(GitHub Pages URL — set DASHBOARD_URL)"


def _guard(section: str, fn):
    """Run a fetcher, converting any hard failure into an empty result."""
    try:
        result = fn()
        if not result:
            record_failure(section, "returned empty result")
        return result
    except Exception as e:  # noqa: BLE001
        record_failure(section, e)
        return None


def _write_step_summary(stale_flags: dict, generated_at: str, dashboard_url: str) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    lines = [
        "## Weekly Market Dashboard run",
        "",
        f"- Generated: `{generated_at}`",
        f"- Dashboard: {dashboard_url}",
        "",
        "### Section status",
    ]
    for name, stale in stale_flags.items():
        state = "⚠️ stale (used cache)" if stale else "✅ fresh"
        lines.append(f"- **{name}**: {state}")
    lines.append("")
    if FAILURES:
        lines.append(f"### Failures ({len(FAILURES)})")
        for f in FAILURES:
            lines.append(f"- `{f}`")
    else:
        lines.append("### Failures\n\nNone 🎉")
    report = "\n".join(lines) + "\n"

    if path:
        try:
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(report)
        except Exception as e:  # noqa: BLE001
            log.warning("could not write step summary: %s", e)
    log.info("\n%s", report)


def run() -> int:
    generated_at = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    dashboard_url = _dashboard_url()
    log.info("=== Weekly Market Dashboard: %s ===", generated_at)

    cache = load_cache()
    cached_data = cache.get("data", {}) if cache else {}

    # ---- Fetch (each guarded) ------------------------------------------
    fresh = {
        "stocks": _guard("fetch_stocks", fetch_stocks),
        "fred": _guard("fetch_fred", fetch_fred),
        "news": _guard("fetch_news", fetch_news),
        "pmi": _guard("scrape_pmi", scrape_all),
    }

    # ---- Merge with cache, track staleness -----------------------------
    data: dict = {}
    stale_flags: dict = {}
    for key in ("stocks", "fred", "news", "pmi"):
        merged, used_cache = merge_section(fresh.get(key), cached_data.get(key))
        data[key] = merged
        stale_flags[key] = used_cache
        if used_cache:
            log.warning("section '%s' is STALE — using cached values", key)

    # ---- Persist cache -------------------------------------------------
    # Only overwrite a section's cache with fresh data (don't re-cache stale).
    new_cache_data = dict(cached_data)
    for key in ("stocks", "fred", "news", "pmi"):
        if fresh.get(key):
            new_cache_data[key] = fresh[key]
    save_cache({"generated_at": generated_at, "data": new_cache_data})

    # ---- Build HTML ----------------------------------------------------
    try:
        html, summary = build_dashboard.build(data, stale_flags, generated_at)
    except Exception as e:  # noqa: BLE001
        record_failure("build_dashboard", e)
        html = f"<html><body><h1>Dashboard build failed</h1><pre>{e}</pre></body></html>"
        summary = f"Dashboard build failed: {e}"

    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    # .nojekyll so GitHub Pages serves files verbatim.
    with open(os.path.join(config.OUTPUT_DIR, ".nojekyll"), "w") as f:
        f.write("")
    with open(config.OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    log.info("Wrote %s (%d bytes)", config.OUTPUT_HTML, len(html))

    # ---- Step summary + email -----------------------------------------
    _write_step_summary(stale_flags, generated_at, dashboard_url)

    text_summary = summary.replace("{dashboard_url}", dashboard_url)
    subject = f"📊 Weekly Market Dashboard — {dt.date.today():%b %d, %Y}"
    send_email(subject, text_summary, summary_to_html(summary, dashboard_url))

    log.info("=== Done. %d failures logged. ===", len(FAILURES))
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
