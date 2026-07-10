"""Assemble the dashboard HTML and the "What Changed This Week" summary.

Pure rendering + light analysis: it takes the merged data dict produced by
main.py and emits (html_string, plain_text_summary). No network calls here,
so it never fails on IO.

Design follows the project's dark data-viz palette: surface #1a1a19, primary
ink #fff, up/green #0ca30c, down/red #d03b3b, sparkline blue #3987e5.
"""

from __future__ import annotations

import datetime as dt
import html
import statistics
from typing import Any

from . import config

# Palette (dark) ------------------------------------------------------------
C_SURFACE = "#1a1a19"
C_PLANE = "#0d0d0d"
C_CARD = "#232322"
C_INK = "#ffffff"
C_INK2 = "#c3c2b7"
C_MUTED = "#898781"
C_GRID = "#2c2c2a"
C_UP = "#0ca30c"
C_DOWN = "#d03b3b"
C_SPARK = "#3987e5"
C_ACCENT = "#eda100"


# --------------------------------------------------------------------------
# Small rendering helpers
# --------------------------------------------------------------------------
def _esc(s: Any) -> str:
    return html.escape(str(s)) if s is not None else ""


def _fmt(v: Any, dp: int = 2, suffix: str = "") -> str:
    if v is None:
        return "—"
    try:
        return f"{float(v):,.{dp}f}{suffix}"
    except (TypeError, ValueError):
        return _esc(v)


def _pct(v: Any, dp: int = 2) -> str:
    if v is None:
        return "—"
    try:
        f = float(v)
        return f"{f:+.{dp}f}%"
    except (TypeError, ValueError):
        return _esc(v)


def _color_for(v: Any) -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return C_INK2
    if f > 0:
        return C_UP
    if f < 0:
        return C_DOWN
    return C_INK2


def sparkline_svg(values: list, width: int = 120, height: int = 30, color: str = C_SPARK) -> str:
    """Inline SVG polyline sparkline with a dot on the last point."""
    pts = [v for v in (values or []) if isinstance(v, (int, float))]
    if len(pts) < 2:
        return f'<svg width="{width}" height="{height}" role="img" aria-label="no data"></svg>'
    lo, hi = min(pts), max(pts)
    span = (hi - lo) or 1.0
    pad = 3
    n = len(pts)
    coords = []
    for i, v in enumerate(pts):
        x = pad + (width - 2 * pad) * (i / (n - 1))
        y = height - pad - (height - 2 * pad) * ((v - lo) / span)
        coords.append((x, y))
    path = " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
    lx, ly = coords[-1]
    trend = C_UP if pts[-1] >= pts[0] else C_DOWN
    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'role="img" aria-label="12-point trend">'
        f'<polyline points="{path}" fill="none" stroke="{trend}" stroke-width="1.6" '
        f'stroke-linejoin="round" stroke-linecap="round"/>'
        f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="2.2" fill="{trend}"/>'
        f"</svg>"
    )


def range_bar(range_pct: Any, low: Any, high: Any, width: int = 130) -> str:
    """Horizontal 52-week range bar with a marker at the current position."""
    if range_pct is None:
        return '<span style="color:#898781">—</span>'
    try:
        p = max(0.0, min(100.0, float(range_pct)))
    except (TypeError, ValueError):
        return '<span style="color:#898781">—</span>'
    marker = p / 100 * (width - 8) + 4
    # Color the marker by proximity to the high end.
    mcol = C_UP if p >= 66 else (C_ACCENT if p >= 33 else C_DOWN)
    return (
        f'<span class="rangewrap" title="Low {_fmt(low)} · High {_fmt(high)}">'
        f'<svg width="{width}" height="14" viewBox="0 0 {width} 14" role="img" '
        f'aria-label="{p:.0f}% of 52-week range">'
        f'<rect x="4" y="5" width="{width - 8}" height="4" rx="2" fill="{C_GRID}"/>'
        f'<rect x="4" y="5" width="{marker - 4:.1f}" height="4" rx="2" fill="{mcol}" opacity="0.55"/>'
        f'<circle cx="{marker:.1f}" cy="7" r="4" fill="{mcol}"/>'
        f"</svg>"
        f'<span class="rangepct">{p:.0f}%</span>'
        f"</span>"
    )


def _arrow(direction: str) -> str:
    return {"up": "▲", "down": "▼"}.get(direction, "▬")


def _arrow_color(direction: str) -> str:
    return {"up": C_UP, "down": C_DOWN}.get(direction, C_MUTED)


def _stale_badge(stale: bool) -> str:
    if not stale:
        return ""
    return '<span class="stale" title="Fresh fetch failed; showing last known value">stale</span>'


# --------------------------------------------------------------------------
# "What Changed This Week" analysis
# --------------------------------------------------------------------------
def analyze_changes(data: dict) -> list[dict]:
    """Return a list of notable-change dicts: {kind, text, tone}."""
    changes: list[dict] = []

    stocks = data.get("stocks", {})
    fred = data.get("fred", {})

    # 1) FRED metrics > threshold std devs vs their ~12-point average.
    for sid, s in fred.items():
        hist = [v for v in s.get("sparkline", []) if isinstance(v, (int, float))]
        latest = s.get("latest_value")
        if latest is None or len(hist) < 4:
            continue
        base = hist[:-1] if len(hist) > 4 else hist
        try:
            mean = statistics.mean(base)
            sd = statistics.pstdev(base)
        except statistics.StatisticsError:
            continue
        if sd <= 0:
            continue
        z = (latest - mean) / sd
        if abs(z) >= config.ZSCORE_THRESHOLD:
            tone = "up" if z > 0 else "down"
            changes.append({
                "kind": "macro",
                "tone": tone,
                "text": f"{s.get('label', sid)} is {abs(z):.1f}σ "
                        f"{'above' if z > 0 else 'below'} its recent average "
                        f"(latest {_fmt(latest, 1)} {s.get('units','')}).",
            })

    # 2) 10Y Treasury weekly move > threshold bps.
    dgs10 = fred.get("DGS10")
    if dgs10 and dgs10.get("weekly_change_bps") is not None:
        bps = dgs10["weekly_change_bps"]
        if abs(bps) >= config.RATE_MOVE_BPS_THRESHOLD:
            changes.append({
                "kind": "rates",
                "tone": "down" if bps > 0 else "up",  # higher yields = headwind
                "text": f"10-Year Treasury yield moved {bps:+.0f} bps this week "
                        f"to {_fmt(dgs10.get('latest_value'), 2)}%.",
            })

    # 3) Biggest stock movers by absolute weekly %.
    movers = [
        (t, s) for t, s in stocks.items()
        if s.get("weekly_pct") is not None and t not in dict(config.MACRO_TICKERS)
    ]
    movers.sort(key=lambda kv: abs(kv[1]["weekly_pct"]), reverse=True)
    for t, s in movers[: config.TOP_MOVERS]:
        wk = s["weekly_pct"]
        changes.append({
            "kind": "mover",
            "tone": "up" if wk > 0 else "down",
            "text": f"{t} ({s.get('label', t)}) {_pct(wk)} on the week.",
        })

    return changes


# --------------------------------------------------------------------------
# Section renderers
# --------------------------------------------------------------------------
def _render_what_changed(changes: list[dict]) -> str:
    if not changes:
        inner = '<p class="empty">Nothing crossed the alert thresholds this week.</p>'
    else:
        rows = []
        for c in changes:
            col = C_UP if c["tone"] == "up" else (C_DOWN if c["tone"] == "down" else C_INK2)
            dot = f'<span class="dot" style="background:{col}"></span>'
            rows.append(f'<li>{dot}{_esc(c["text"])}</li>')
        inner = f'<ul class="changes">{"".join(rows)}</ul>'
    return f"""
    <section class="callout" id="what-changed">
      <h2>⚡ What Changed This Week</h2>
      {inner}
    </section>"""


def _render_macro_row(stocks: dict, stale: bool) -> str:
    cards = []
    for ticker, label in config.MACRO_TICKERS:
        s = stocks.get(ticker)
        if not s:
            cards.append(f"""
            <div class="mcard">
              <div class="mlabel">{_esc(ticker)}</div>
              <div class="mval">—</div>
              <div class="msub">data unavailable</div>
            </div>""")
            continue
        wk = s.get("weekly_pct")
        cards.append(f"""
        <div class="mcard">
          <div class="mlabel">{_esc(ticker)} <span class="mname">{_esc(label)}</span></div>
          <div class="mval">{_fmt(s.get('last'))}</div>
          <div class="msub" style="color:{_color_for(wk)}">{_pct(wk)} wk
            <span class="ytd">· YTD {_pct(s.get('ytd_pct'))}</span></div>
          <div class="mspark">{sparkline_svg(s.get('sparkline'), 150, 34)}</div>
        </div>""")
    return f"""
    <section class="block">
      <h2>Macro Snapshot {_stale_badge(stale)}</h2>
      <div class="macro-grid">{"".join(cards)}</div>
    </section>"""


def _render_fred(fred: dict, stale: bool) -> str:
    if not fred:
        return _unavailable("Manufacturing & Macro Indicators (FRED)")
    rows = []
    for spec in config.FRED_SERIES:
        sid = spec["id"]
        s = fred.get(sid)
        if not s:
            rows.append(f'<tr><td>{_esc(spec["label"])}</td>'
                        f'<td colspan="4" class="na">data unavailable this week</td></tr>')
            continue
        arrow = _arrow(s.get("direction", "flat"))
        acol = _arrow_color(s.get("direction", "flat"))
        change_cell = ""
        if s.get("is_bps") and s.get("weekly_change_bps") is not None:
            bc = _color_for(s["weekly_change_bps"])
            change_cell = f'<span style="color:{bc}">{s["weekly_change_bps"]:+.0f} bps/wk</span>'
        elif s.get("prior_value") is not None:
            diff = s["latest_value"] - s["prior_value"]
            change_cell = f'<span style="color:{_color_for(diff)}">{diff:+,.2f} vs prior</span>'
        rows.append(f"""
        <tr>
          <td class="fname">{_esc(s.get('label', sid))}</td>
          <td class="num">{_fmt(s.get('latest_value'), 2)}
              <span class="unit">{_esc(s.get('units',''))}</span></td>
          <td class="num prior">{_fmt(s.get('prior_value'), 2)}</td>
          <td class="dir" style="color:{acol}">{arrow} {change_cell}</td>
          <td class="rel">{_esc(s.get('latest_date',''))}
              <span class="spark">{sparkline_svg(s.get('sparkline'), 90, 24)}</span></td>
        </tr>""")
    return f"""
    <section class="block">
      <h2>Manufacturing &amp; Macro Indicators {_stale_badge(stale)}</h2>
      <div class="tablewrap">
      <table class="data">
        <thead><tr><th>Series</th><th>Latest</th><th>Prior</th>
          <th>Direction</th><th>Release date / trend</th></tr></thead>
        <tbody>{"".join(rows)}</tbody>
      </table></div>
      <p class="foot">Series publish on different lags — each row is labelled with its own observation date.</p>
    </section>"""


def _render_pmi(pmi: dict, fred: dict) -> str:
    ism = (pmi or {}).get("ism_pmi", {})
    if ism.get("available"):
        v = ism["value"]
        state = "Expansion" if ism.get("expansion") else "Contraction"
        scol = C_UP if ism.get("expansion") else C_DOWN
        period = f" · {_esc(ism.get('period'))}" if ism.get("period") else ""
        body = f"""
        <div class="pmi-hero">
          <div class="pmi-num" style="color:{scol}">{v:.1f}</div>
          <div class="pmi-meta">
            <div class="pmi-state" style="color:{scol}">{state}</div>
            <div class="pmi-sub">ISM Manufacturing PMI{period} · 50 = neutral</div>
          </div>
        </div>"""
    else:
        note = (pmi or {}).get("ism_pmi", {}).get("note", "ISM PMI unavailable.")
        proxy = []
        for sid in config.PMI_PROXY_SERIES:
            s = fred.get(sid)
            if s:
                acol = _arrow_color(s.get("direction", "flat"))
                proxy.append(
                    f'<div class="proxy"><span class="pxl">{_esc(s.get("label", sid))}</span>'
                    f'<span class="pxv" style="color:{acol}">{_fmt(s.get("latest_value"),1)} '
                    f'{_arrow(s.get("direction","flat"))}</span>'
                    f'<span class="pxd">{_esc(s.get("latest_date",""))}</span></div>'
                )
        body = (f'<p class="note">⚠ {_esc(note)}</p>'
                f'<div class="proxies">{"".join(proxy) or "<span class=na>Proxies also unavailable.</span>"}</div>')
    return f"""
    <section class="block">
      <h2>Manufacturing PMI</h2>
      {body}
    </section>"""


def _render_freight(pmi: dict) -> str:
    cass = (pmi or {}).get("cass", {})
    aar = (pmi or {}).get("aar", {})

    def _card(title: str, d: dict) -> str:
        if d.get("available"):
            return (f'<div class="fcard"><div class="ftitle">{_esc(title)}</div>'
                    f'<div class="fbody">{_esc(d.get("headline",""))}</div>'
                    f'<a class="fsrc" href="{_esc(d.get("source",""))}">source ↗</a></div>')
        return (f'<div class="fcard"><div class="ftitle">{_esc(title)}</div>'
                f'<div class="fbody na">{_esc(d.get("note","data unavailable this week"))}</div></div>')

    return f"""
    <section class="block">
      <h2>Freight</h2>
      <div class="freight-grid">
        {_card("Cass Freight Index", cass)}
        {_card("AAR Weekly Rail Traffic", aar)}
      </div>
    </section>"""


def _render_watchlist(stocks: dict, stale: bool) -> str:
    if not stocks:
        return _unavailable("Watchlist")
    groups_html = []
    for group_name, members in config.WATCHLIST_GROUPS.items():
        rows = []
        for ticker, label in members:
            s = stocks.get(ticker)
            if not s:
                rows.append(f'<tr><td class="tk">{_esc(ticker)}</td>'
                            f'<td colspan="5" class="na">data unavailable this week</td></tr>')
                continue
            wk, ytd = s.get("weekly_pct"), s.get("ytd_pct")
            rows.append(f"""
            <tr>
              <td class="tk">{_esc(ticker)}<span class="tname">{_esc(label)}</span></td>
              <td class="num">{_fmt(s.get('last'))}</td>
              <td class="num" style="color:{_color_for(wk)}">{_pct(wk)}</td>
              <td class="num" style="color:{_color_for(ytd)}">{_pct(ytd)}</td>
              <td class="rng">{range_bar(s.get('range_pct'), s.get('low_52w'), s.get('high_52w'))}</td>
              <td class="spk">{sparkline_svg(s.get('sparkline'), 110, 26)}</td>
            </tr>""")
        groups_html.append(f"""
        <tbody class="grp">
          <tr class="grphead"><td colspan="6">{_esc(group_name)}</td></tr>
          {"".join(rows)}
        </tbody>""")
    return f"""
    <section class="block">
      <h2>Watchlist {_stale_badge(stale)}</h2>
      <div class="tablewrap">
      <table class="data watch">
        <thead><tr><th>Ticker</th><th>Last</th><th>Week</th><th>YTD</th>
          <th>52-wk range</th><th>12-wk trend</th></tr></thead>
        {"".join(groups_html)}
      </table></div>
    </section>"""


def _render_news(news: dict, stocks: dict) -> str:
    news = news or {}
    tickers = news.get("tickers", {})
    macro = news.get("macro", [])
    if not tickers and not macro:
        return _unavailable("News")

    def _item(it: dict) -> str:
        src = f' · <span class="nsrc">{_esc(it.get("source",""))}</span>' if it.get("source") else ""
        return (f'<li><a href="{_esc(it.get("link","#"))}" target="_blank" rel="noopener">'
                f'{_esc(it.get("title",""))}</a>{src}</li>')

    blocks = []
    if macro:
        items = "".join(_item(it) for it in macro)
        blocks.append(f'<div class="newsgrp macro"><h3>🌐 Macro &amp; Policy</h3>'
                      f'<ul class="newslist">{items}</ul></div>')

    for group_name, members in config.WATCHLIST_GROUPS.items():
        for ticker, label in members:
            items = tickers.get(ticker)
            if not items:
                continue
            lis = "".join(_item(it) for it in items)
            blocks.append(f'<div class="newsgrp"><h3>{_esc(ticker)} '
                          f'<span class="nname">{_esc(label)}</span></h3>'
                          f'<ul class="newslist">{lis}</ul></div>')

    return f"""
    <section class="block">
      <h2>News <span class="foot inline">past {config.NEWS_LOOKBACK_DAYS} days</span></h2>
      <div class="news-grid">{"".join(blocks)}</div>
    </section>"""


def _unavailable(title: str) -> str:
    return f"""
    <section class="block">
      <h2>{_esc(title)}</h2>
      <p class="na big">Data unavailable this week.</p>
    </section>"""


# --------------------------------------------------------------------------
# Top-level build
# --------------------------------------------------------------------------
def build(data: dict, stale_flags: dict, generated_at: str) -> tuple[str, str]:
    """Return (html, plain_text_summary)."""
    changes = analyze_changes(data)

    stocks = data.get("stocks", {})
    fred = data.get("fred", {})
    news = data.get("news", {})
    pmi = data.get("pmi", {})

    sections = "".join([
        _render_what_changed(changes),
        _render_macro_row(stocks, stale_flags.get("stocks", False)),
        _render_fred(fred, stale_flags.get("fred", False)),
        _render_pmi(pmi, fred),
        _render_freight(pmi),
        _render_watchlist(stocks, stale_flags.get("stocks", False)),
        _render_news(news, stocks),
    ])

    any_stale = any(stale_flags.values())
    stale_note = ('<span class="hstale">· some sections show last known values</span>'
                  if any_stale else "")

    page = _PAGE_TEMPLATE.format(
        css=_CSS,
        generated_at=_esc(generated_at),
        stale_note=stale_note,
        sections=sections,
    )

    summary = _build_text_summary(changes, generated_at)
    return page, summary


def _build_text_summary(changes: list[dict], generated_at: str) -> str:
    lines = [f"Weekly Market Dashboard — {generated_at}", ""]
    lines.append("WHAT CHANGED THIS WEEK")
    if not changes:
        lines.append("  • Nothing crossed the alert thresholds this week.")
    else:
        for c in changes:
            mark = {"up": "▲", "down": "▼"}.get(c["tone"], "•")
            lines.append(f"  {mark} {c['text']}")
    lines.append("")
    lines.append("Full dashboard: {dashboard_url}")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# CSS + HTML shell
# --------------------------------------------------------------------------
_CSS = """
:root{--surface:#1a1a19;--plane:#0d0d0d;--card:#232322;--ink:#fff;--ink2:#c3c2b7;
--muted:#898781;--grid:#2c2c2a;--up:#0ca30c;--down:#d03b3b;--spark:#3987e5;--accent:#eda100;}
*{box-sizing:border-box;}
body{margin:0;background:var(--plane);color:var(--ink);
font-family:system-ui,-apple-system,"Segoe UI",sans-serif;line-height:1.5;
-webkit-text-size-adjust:100%;}
.wrap{max-width:1040px;margin:0 auto;padding:16px;}
header.top{padding:22px 4px 6px;}
header.top h1{margin:0;font-size:1.5rem;letter-spacing:-0.02em;}
header.top .sub{color:var(--muted);font-size:0.85rem;margin-top:4px;}
.hstale{color:var(--accent);}
h2{font-size:1.05rem;margin:0 0 12px;letter-spacing:-0.01em;}
h3{font-size:0.9rem;margin:0 0 8px;color:var(--ink);}
.block,.callout{background:var(--surface);border:1px solid rgba(255,255,255,0.07);
border-radius:14px;padding:18px;margin:14px 0;}
.callout{border-color:rgba(237,161,0,0.35);background:linear-gradient(180deg,#201d13,#1a1a19);}
.callout h2{color:var(--accent);}
ul.changes{list-style:none;margin:0;padding:0;}
ul.changes li{padding:7px 0;border-bottom:1px solid var(--grid);font-size:0.95rem;
display:flex;align-items:baseline;gap:10px;}
ul.changes li:last-child{border-bottom:none;}
.dot{width:8px;height:8px;border-radius:50%;flex:0 0 auto;display:inline-block;transform:translateY(1px);}
.empty,.foot{color:var(--muted);font-size:0.82rem;}
.foot.inline{font-weight:400;}
.macro-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;}
.mcard{background:var(--card);border-radius:10px;padding:12px;}
.mlabel{font-weight:600;font-size:0.95rem;}
.mname{color:var(--muted);font-weight:400;font-size:0.75rem;display:block;}
.mval{font-size:1.5rem;font-weight:600;margin:2px 0;font-variant-numeric:tabular-nums;}
.msub{font-size:0.82rem;font-variant-numeric:tabular-nums;}
.ytd{color:var(--muted);}
.mspark{margin-top:6px;}
.tablewrap{overflow-x:auto;-webkit-overflow-scrolling:touch;}
table.data{width:100%;border-collapse:collapse;font-size:0.88rem;}
table.data th{text-align:left;color:var(--muted);font-weight:500;font-size:0.75rem;
text-transform:uppercase;letter-spacing:0.04em;padding:6px 10px;border-bottom:1px solid var(--grid);}
table.data td{padding:9px 10px;border-bottom:1px solid var(--grid);vertical-align:middle;}
.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap;}
.prior{color:var(--muted);}
.unit{color:var(--muted);font-size:0.72rem;}
.fname,.fname{font-weight:500;}
.dir{white-space:nowrap;font-variant-numeric:tabular-nums;font-size:0.82rem;}
.rel{color:var(--muted);font-size:0.78rem;white-space:nowrap;}
.rel .spark{margin-left:8px;vertical-align:middle;}
.tk{font-weight:600;}
.tname{display:block;color:var(--muted);font-weight:400;font-size:0.72rem;}
.grphead td{color:var(--accent);font-size:0.72rem;text-transform:uppercase;
letter-spacing:0.06em;padding-top:14px;font-weight:600;border-bottom:1px solid var(--grid);}
.watch .rng{min-width:150px;}
.rangewrap{display:inline-flex;align-items:center;gap:6px;}
.rangepct{font-size:0.72rem;color:var(--muted);font-variant-numeric:tabular-nums;}
.spk{text-align:right;}
.na{color:var(--muted);font-style:italic;}
.na.big{padding:8px 0;}
.pmi-hero{display:flex;align-items:center;gap:18px;}
.pmi-num{font-size:3rem;font-weight:700;font-variant-numeric:tabular-nums;line-height:1;}
.pmi-state{font-weight:600;font-size:1rem;}
.pmi-sub{color:var(--muted);font-size:0.82rem;}
.note{color:var(--accent);font-size:0.86rem;margin:0 0 12px;}
.proxies{display:flex;flex-wrap:wrap;gap:12px;}
.proxy{background:var(--card);border-radius:8px;padding:10px 12px;min-width:150px;}
.pxl{display:block;font-size:0.78rem;color:var(--ink2);}
.pxv{font-size:1.15rem;font-weight:600;font-variant-numeric:tabular-nums;}
.pxd{display:block;color:var(--muted);font-size:0.72rem;}
.freight-grid,.news-grid{display:grid;gap:12px;}
.freight-grid{grid-template-columns:repeat(auto-fit,minmax(240px,1fr));}
.fcard{background:var(--card);border-radius:10px;padding:14px;}
.ftitle{font-weight:600;margin-bottom:6px;}
.fbody{font-size:0.9rem;color:var(--ink2);}
.fsrc{display:inline-block;margin-top:8px;font-size:0.75rem;color:var(--spark);text-decoration:none;}
.news-grid{grid-template-columns:repeat(auto-fit,minmax(280px,1fr));}
.newsgrp{background:var(--card);border-radius:10px;padding:14px;}
.newsgrp.macro{grid-column:1/-1;border:1px solid rgba(57,135,229,0.25);}
.nname,.nsrc{color:var(--muted);font-weight:400;font-size:0.78rem;}
ul.newslist{list-style:none;margin:0;padding:0;}
ul.newslist li{padding:6px 0;border-bottom:1px solid var(--grid);font-size:0.88rem;}
ul.newslist li:last-child{border-bottom:none;}
ul.newslist a{color:var(--ink);text-decoration:none;}
ul.newslist a:hover{color:var(--spark);text-decoration:underline;}
.stale{background:var(--down);color:#fff;font-size:0.6rem;padding:2px 6px;border-radius:6px;
vertical-align:middle;margin-left:8px;text-transform:uppercase;letter-spacing:0.05em;}
footer.bot{color:var(--muted);font-size:0.78rem;text-align:center;padding:24px 0 40px;}
footer.bot a{color:var(--spark);}
@media (max-width:560px){
  header.top h1{font-size:1.25rem;}
  .pmi-num{font-size:2.2rem;}
  .block,.callout{padding:14px;}
}
"""

_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark">
<title>Weekly Market Dashboard</title>
<style>{css}</style>
</head>
<body>
<div class="wrap">
  <header class="top">
    <h1>Weekly Market Dashboard</h1>
    <div class="sub">Industrial · Logistics · Retail · Macro &nbsp;—&nbsp;
      generated {generated_at} {stale_note}</div>
  </header>
  {sections}
  <footer class="bot">
    Built automatically every Monday · data from Yahoo Finance, FRED, ISM, Cass, AAR &amp; Google News.<br>
    Not investment advice.
  </footer>
</div>
</body>
</html>"""
