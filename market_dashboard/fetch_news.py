"""Fetch headlines from Google News RSS.

Per equity ticker: top N headlines from the past `NEWS_LOOKBACK_DAYS` days.
Plus a handful of macro headlines (Fed, tariffs, manufacturing, freight).

Google News RSS needs no API key. We dedupe near-identical headlines with a
cheap token-overlap heuristic so the same story from three outlets collapses
to one line.
"""

from __future__ import annotations

import datetime as dt
import re
import urllib.parse
from xml.etree import ElementTree as ET

from . import config
from .utils import http_session, log, record_failure, retry

_RSS = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
_WORD_RE = re.compile(r"[a-z0-9]+")
_STOP = {
    "the", "a", "an", "to", "of", "in", "on", "for", "and", "or", "with",
    "as", "at", "by", "from", "is", "are", "be", "its", "new", "amid",
    "says", "after", "over", "will", "into", "up", "down",
}


def _tokens(title: str) -> set[str]:
    words = [w for w in _WORD_RE.findall(title.lower()) if w not in _STOP and len(w) > 2]
    return set(words)


def _similar(a: set[str], b: set[str], threshold: float = 0.6) -> bool:
    if not a or not b:
        return False
    overlap = len(a & b) / len(a | b)
    return overlap >= threshold


def _dedupe(items: list[dict]) -> list[dict]:
    kept: list[dict] = []
    kept_tokens: list[set[str]] = []
    for it in items:
        toks = _tokens(it["title"])
        if any(_similar(toks, kt) for kt in kept_tokens):
            continue
        kept.append(it)
        kept_tokens.append(toks)
    return kept


def _parse_rss(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    out = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        source_el = item.find("{*}source")
        source = source_el.text.strip() if source_el is not None and source_el.text else ""
        when = None
        for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%a, %d %b %Y %H:%M:%S %z"):
            try:
                when = dt.datetime.strptime(pub, fmt)
                break
            except ValueError:
                continue
        if not title:
            continue
        out.append({"title": title, "link": link, "source": source, "published": when, "pub_raw": pub})
    return out


def _query(session, query: str, limit: int) -> list[dict]:
    url = _RSS.format(query=urllib.parse.quote(query))

    def _do():
        r = session.get(url, timeout=config.HTTP_TIMEOUT)
        r.raise_for_status()
        return r.text

    xml_text = retry(_do, 3, 2.0, f"news[{query}]")
    items = _parse_rss(xml_text)

    # Filter to the lookback window (keep items with no parseable date).
    cutoff = dt.datetime.now() - dt.timedelta(days=config.NEWS_LOOKBACK_DAYS)
    fresh = []
    for it in items:
        pub = it.get("published")
        if pub is not None:
            pub_naive = pub.replace(tzinfo=None)
            if pub_naive < cutoff:
                continue
            it["published"] = pub_naive.isoformat()
        fresh.append(it)

    fresh = _dedupe(fresh)
    # Serialize datetimes for caching.
    for it in fresh:
        if isinstance(it.get("published"), dt.datetime):
            it["published"] = it["published"].isoformat()
    return fresh[:limit]


def fetch_news() -> dict:
    """Return {"tickers": {ticker: [items]}, "macro": [items]}."""
    session = http_session()
    result = {"tickers": {}, "macro": []}

    for ticker in config.ALL_TICKERS:
        label = config.TICKER_LABELS.get(ticker, ticker)
        # Company name search is more relevant than the raw symbol.
        q = f'"{label}" OR {ticker} stock'
        try:
            items = _query(session, q, config.NEWS_HEADLINES_PER_TICKER)
            if items:
                result["tickers"][ticker] = items
                log.info("news  %-10s %d headlines", ticker, len(items))
        except Exception as e:  # noqa: BLE001
            record_failure(f"fetch_news[{ticker}]", e)

    # Macro topics: gather then dedupe across topics, keep top MACRO_NEWS_TOTAL.
    macro_pool: list[dict] = []
    for query, tag in config.MACRO_NEWS_TOPICS:
        try:
            items = _query(session, query, 3)
            for it in items:
                it["topic"] = tag
            macro_pool.extend(items)
        except Exception as e:  # noqa: BLE001
            record_failure(f"fetch_news/macro[{tag}]", e)

    macro_pool = _dedupe(macro_pool)
    result["macro"] = macro_pool[: config.MACRO_NEWS_TOTAL]
    log.info("news  macro    %d headlines", len(result["macro"]))
    return result


if __name__ == "__main__":
    import json

    print(json.dumps(fetch_news(), indent=2, default=str))
