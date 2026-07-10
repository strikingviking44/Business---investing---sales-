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
from .utils import explain_status, http_session, log, record_failure, retry


def _get(session, url: str) -> str:
    """Fetch a page, logging the URL, HTTP status, and body size each time."""

    def _do():
        r = session.get(url, timeout=config.HTTP_TIMEOUT)
        ctype = r.headers.get("Content-Type", "?")
        log.info("scrape GET %s -> HTTP %s, %d bytes, %s",
                 url, r.status_code, len(r.content or b""), ctype)
        if r.status_code >= 400:
            log.error("scrape %s HTTP %s — %s", url, r.status_code, explain_status(r.status_code))
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


def _snippet(text: str, keywords: list[str], width: int = 240) -> str:
    """Return a short excerpt around the first keyword hit, for debug logs.

    Lets us see, from the Action log, what the page actually contained when
    parsing failed — usually revealing a JS-only shell or a changed layout.
    """
    low = text.lower()
    for kw in keywords:
        i = low.find(kw.lower())
        if i >= 0:
            start = max(0, i - 60)
            return text[start:start + width].replace("\n", " ")
    return text[:width].replace("\n", " ")


def scrape_ism_pmi() -> dict:
    """Scrape the headline ISM Manufacturing PMI value."""
    session = http_session()
    try:
        html = _get(session, config.ISM_PMI_URL)
        text = _text(html)

        # Look for phrases like "PMI registered 48.7 percent",
        # "Manufacturing PMI ... 50.9%", "PMI® ... 48.5", "PMI at 49.0".
        patterns = [
            r"PMI[^.]{0,60}?registered\s+([0-9]{1,3}(?:\.[0-9])?)",
            r"Manufacturing PMI[^0-9]{0,60}?([0-9]{1,3}(?:\.[0-9])?)\s*(?:percent|%)",
            r"PMI[®\s]{0,4}(?:at|was|of|reading of)?\s*([0-9]{1,3}\.[0-9])\s*(?:percent|%)?",
            r"PMI[^0-9]{0,30}?([0-9]{1,3}\.[0-9])",
        ]
        value = None
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                try:
                    cand = float(m.group(1))
                except ValueError:
                    continue
                if 20 <= cand <= 80:  # sane PMI band
                    value = cand
                    break

        if value is None:
            log.error("scrape_ism_pmi: no PMI value parsed. Page excerpt: %s",
                      _snippet(text, ["PMI", "Manufacturing"]))
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

        # Cass commentary states a YoY change on shipments/expenditures, e.g.
        # "shipments ... fell 3.2% ...", "shipments component ... declined 5.1
        # percent", "expenditures were down 2%". Allow the verb and the number
        # to sit some distance apart, and accept integer or decimal percents.
        patterns = [
            r"(shipments|expenditures)[^.]{0,160}?"
            r"(rose|fell|declined|increased|decreased|dropped|gained|were up|were down|up|down)"
            r"[^.0-9]{0,20}?([0-9]{1,2}(?:\.[0-9])?)\s*(?:percent|%)",
            r"(rose|fell|declined|increased|decreased|dropped|gained|up|down)"
            r"[^.0-9]{0,20}?([0-9]{1,2}(?:\.[0-9])?)\s*(?:percent|%)[^.]{0,80}?"
            r"(shipments|expenditures)",
        ]
        headline = None
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                headline = re.sub(r"\s+", " ", m.group(0)).strip()[:180]
                break

        if not headline:
            log.error("scrape_cass_freight: no figure parsed. Page excerpt: %s",
                      _snippet(text, ["shipments", "expenditures", "freight index"]))
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

        # AAR reports weekly U.S. carloads / intermodal units vs the year-ago
        # week, e.g. "total carloads ... were up 1.2 percent", "intermodal
        # ... down 3%", "combined ... rose 2.4%".
        patterns = [
            r"(carloads?|intermodal(?:\s+units)?|rail traffic|combined[^.]{0,20}traffic)"
            r"[^.]{0,160}?(up|down|rose|fell|increased|decreased|were up|were down|gained|declined)"
            r"[^.0-9]{0,20}?([0-9]{1,2}(?:\.[0-9])?)\s*(?:percent|%)",
            r"(up|down|rose|fell|increased|decreased|gained|declined)"
            r"[^.0-9]{0,20}?([0-9]{1,2}(?:\.[0-9])?)\s*(?:percent|%)[^.]{0,80}?"
            r"(carloads?|intermodal|rail traffic)",
        ]
        headline = None
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                headline = re.sub(r"\s+", " ", m.group(0)).strip()[:180]
                break

        if not headline:
            log.error("scrape_aar_rail: no figure parsed. Page excerpt: %s",
                      _snippet(text, ["carloads", "intermodal", "rail traffic"]))
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
