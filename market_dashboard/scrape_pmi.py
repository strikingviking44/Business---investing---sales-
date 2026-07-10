"""Best-effort scrapers for ISM Manufacturing PMI, Cass Freight Index, and
AAR weekly rail traffic.

These are public HTML pages with no stable API, so scraping is inherently
fragile. Every function follows the same contract: return a dict on success,
or a dict with {"available": False, "note": ...} on failure — never raise.
The dashboard renders a graceful "data unavailable this week" note and, for
PMI specifically, falls back to the Empire/Philly Fed proxies.
"""

from __future__ import annotations

import re

from . import config
from .utils import http_session, log, record_failure, retry


def _get(session, url: str) -> str:
    def _do():
        r = session.get(url, timeout=config.HTTP_TIMEOUT)
        r.raise_for_status()
        return r.text

    return retry(_do, 3, 2.0, f"scrape[{url}]")


def _text(html: str) -> str:
    """Strip tags to plain text for regex scanning."""
    try:
        from bs4 import BeautifulSoup

        return BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    except Exception:  # noqa: BLE001
        # Fallback: crude tag strip.
        return re.sub(r"<[^>]+>", " ", html)


def scrape_ism_pmi() -> dict:
    """Scrape the headline ISM Manufacturing PMI value."""
    session = http_session()
    try:
        html = _get(session, config.ISM_PMI_URL)
        text = _text(html)

        # Look for phrases like "PMI registered 48.7 percent" or
        # "Manufacturing PMI ... 50.9%".
        patterns = [
            r"PMI[^.]{0,40}?registered\s+([0-9]{1,3}\.[0-9])",
            r"Manufacturing PMI[^0-9]{0,40}?([0-9]{1,3}\.[0-9])\s*(?:percent|%)",
            r"PMI[^0-9]{0,20}?([0-9]{1,3}\.[0-9])\s*(?:percent|%)",
        ]
        value = None
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                value = float(m.group(1))
                break

        if value is None or not (20 <= value <= 80):
            raise ValueError("could not locate a plausible PMI headline value")

        # Try to find a month/year label nearby.
        month_m = re.search(
            r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}",
            text,
        )
        period = month_m.group(0) if month_m else None

        log.info("scrape ISM PMI = %s (%s)", value, period)
        return {
            "available": True,
            "value": value,
            "period": period,
            "expansion": value >= 50.0,
            "source": config.ISM_PMI_URL,
        }
    except Exception as e:  # noqa: BLE001
        record_failure("scrape_ism_pmi", e)
        return {
            "available": False,
            "note": "ISM PMI scrape failed — showing Empire/Philly Fed proxies instead.",
        }


def scrape_cass_freight() -> dict:
    """Scrape a headline figure from the Cass Freight Index page."""
    session = http_session()
    try:
        html = _get(session, config.CASS_FREIGHT_URL)
        text = _text(html)

        # Cass commentary typically states YoY change, e.g.
        # "shipments ... fell 3.2% ... " or "index ... 9.8".
        m = re.search(
            r"(shipments|expenditures)[^.]{0,120}?(rose|fell|declined|increased|decreased|up|down)\s+([0-9]{1,2}\.[0-9])\s*(?:percent|%)",
            text,
            re.IGNORECASE,
        )
        headline = None
        if m:
            headline = re.sub(r"\s+", " ", m.group(0)).strip()[:180]

        if not headline:
            raise ValueError("no Cass headline figure found")

        log.info("scrape Cass = %s", headline)
        return {"available": True, "headline": headline, "source": config.CASS_FREIGHT_URL}
    except Exception as e:  # noqa: BLE001
        record_failure("scrape_cass_freight", e)
        return {"available": False, "note": "Cass Freight Index unavailable this week."}


def scrape_aar_rail() -> dict:
    """Scrape a headline figure from the AAR weekly rail traffic page."""
    session = http_session()
    try:
        html = _get(session, config.AAR_RAIL_URL)
        text = _text(html)

        m = re.search(
            r"(carloads?|intermodal|rail traffic)[^.]{0,140}?(up|down|rose|fell|increased|decreased)\s+([0-9]{1,2}(?:\.[0-9])?)\s*(?:percent|%)",
            text,
            re.IGNORECASE,
        )
        headline = None
        if m:
            headline = re.sub(r"\s+", " ", m.group(0)).strip()[:180]

        if not headline:
            raise ValueError("no AAR headline figure found")

        log.info("scrape AAR = %s", headline)
        return {"available": True, "headline": headline, "source": config.AAR_RAIL_URL}
    except Exception as e:  # noqa: BLE001
        record_failure("scrape_aar_rail", e)
        return {"available": False, "note": "AAR rail traffic unavailable this week."}


def scrape_all() -> dict:
    return {
        "ism_pmi": scrape_ism_pmi(),
        "cass": scrape_cass_freight(),
        "aar": scrape_aar_rail(),
    }


if __name__ == "__main__":
    import json

    print(json.dumps(scrape_all(), indent=2, default=str))
