"""Fetch macro series from the FRED API.

For each series we return the latest observation, the prior observation, a
direction, the release/observation date (series publish on different lags,
so we label each), and a sparkline. DGS10 additionally gets its weekly change
expressed in basis points.

Requires FRED_API_KEY in the environment. If it's missing or any request
fails, the affected series is omitted and main.py falls back to cache.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from . import config
from .utils import (
    explain_status,
    gh_error,
    http_session,
    http_status_of,
    log,
    mask,
    record_failure,
    retry,
)


def _to_float(x: str) -> float | None:
    try:
        if x in (".", "", None):
            return None
        return float(x)
    except (TypeError, ValueError):
        return None


def _fetch_series(session, series_id: str, start: str) -> list[dict]:
    url = f"{config.FRED_BASE}/series/observations"
    params = {
        "series_id": series_id,
        "api_key": config.FRED_API_KEY,
        "file_type": "json",
        "observation_start": start,
        "sort_order": "asc",
    }

    def _do():
        r = session.get(url, params=params, timeout=config.HTTP_TIMEOUT)
        # Log status on any non-2xx BEFORE raising, so the run log shows
        # whether this is a bad key (400/403), rate limit (429), etc. FRED
        # returns a helpful error_message body on 400 — surface it.
        if r.status_code >= 400:
            hint = explain_status(r.status_code)
            detail = ""
            try:
                body = r.json()
                detail = body.get("error_message", "")
            except Exception:  # noqa: BLE001
                detail = (r.text or "")[:200]
            log.error("FRED[%s] HTTP %s — %s %s", series_id, r.status_code, hint, detail)
        r.raise_for_status()
        return r.json()

    payload = retry(_do, 3, 2.0, f"FRED[{series_id}]")
    obs = payload.get("observations", [])
    cleaned = []
    for o in obs:
        v = _to_float(o.get("value"))
        if v is not None:
            cleaned.append({"date": o["date"], "value": v})
    return cleaned


def _direction(latest: float, prior: float | None) -> str:
    if prior is None:
        return "flat"
    if latest > prior:
        return "up"
    if latest < prior:
        return "down"
    return "flat"


def fetch_fred() -> dict[str, dict]:
    """Return {series_id: {...}} for every configured FRED series."""
    if not config.FRED_API_KEY.strip():
        gh_error(
            "fetch_fred: FRED_API_KEY not set — every FRED/macro section will be "
            "empty. Add the FRED_API_KEY repository secret and re-run."
        )
        record_failure("fetch_fred", "FRED_API_KEY not set")
        return {}

    log.info("fetch_fred: FRED_API_KEY %s", mask(config.FRED_API_KEY))
    session = http_session()
    results: dict[str, dict] = {}
    today = dt.date.today()
    status_hints: set[str] = set()

    for spec in config.FRED_SERIES:
        sid = spec["id"]
        months = spec.get("sparkline_months", 12)
        # Pull a bit more history than the sparkline needs for headroom.
        start = (today - dt.timedelta(days=int(months * 31) + 45)).strftime("%Y-%m-%d")
        try:
            series = _fetch_series(session, sid, start)
            if len(series) < 1:
                record_failure(f"fetch_fred[{sid}]", "no observations")
                continue

            latest = series[-1]
            prior = series[-2] if len(series) >= 2 else None
            prior_val = prior["value"] if prior else None

            entry: dict[str, Any] = {
                "id": sid,
                "label": spec["label"],
                "units": spec.get("units", ""),
                "latest_value": latest["value"],
                "latest_date": latest["date"],
                "prior_value": prior_val,
                "prior_date": prior["date"] if prior else None,
                "direction": _direction(latest["value"], prior_val),
                "sparkline": [round(p["value"], 3) for p in series[-(months * 5):]] or [latest["value"]],
                "is_bps": spec.get("bps", False),
            }

            # Weekly change in bps for rate series (values are in percent).
            if spec.get("bps"):
                # Find the observation closest to ~7 days before latest.
                latest_date = dt.date.fromisoformat(latest["date"])
                target = latest_date - dt.timedelta(days=7)
                week_ago = None
                for p in reversed(series[:-1]):
                    if dt.date.fromisoformat(p["date"]) <= target:
                        week_ago = p
                        break
                if week_ago is None and prior:
                    week_ago = prior
                if week_ago is not None:
                    entry["weekly_change_bps"] = round((latest["value"] - week_ago["value"]) * 100, 1)
                    entry["week_ago_date"] = week_ago["date"]

            results[sid] = entry
            log.info("fred  %-20s %s (%s)", sid, latest["value"], latest["date"])
        except Exception as e:  # noqa: BLE001
            code = http_status_of(e)
            hint = explain_status(code)
            status_hints.add(hint)
            record_failure(f"fetch_fred[{sid}]", f"{e} ({hint})")

    # If nothing came back, say why loudly and point at the likely cause.
    if not results:
        if any("key" in h for h in status_hints):
            gh_error(
                "fetch_fred: all FRED series failed with an auth error — the "
                "FRED_API_KEY value is set but appears INVALID. Regenerate it at "
                "https://fredaccount.stlouisfed.org/apikeys and update the secret."
            )
        elif any("429" in h for h in status_hints):
            gh_error("fetch_fred: all FRED series were rate-limited (429). Re-run shortly.")
        else:
            gh_error(
                "fetch_fred: every FRED series failed. Status hints: "
                + (", ".join(sorted(status_hints)) or "network/timeout")
            )

    return results


if __name__ == "__main__":
    import json

    print(json.dumps(fetch_fred(), indent=2, default=str))
