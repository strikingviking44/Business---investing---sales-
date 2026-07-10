"""Send the weekly summary email via Gmail SMTP.

Uses an app password (not the account password). Credentials come from env:
  GMAIL_ADDRESS       — the sending & receiving address
  GMAIL_APP_PASSWORD  — a 16-char Google app password

If either is missing we skip email (and log it) rather than crash — useful
for local test runs.
"""

from __future__ import annotations

import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .utils import log, record_failure

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465


def send_email(subject: str, text_body: str, html_body: str | None = None,
               to_addr: str | None = None) -> bool:
    address = os.environ.get("GMAIL_ADDRESS", "").strip()
    password = os.environ.get("GMAIL_APP_PASSWORD", "").strip()
    recipient = (to_addr or address).strip()

    if not address or not password:
        record_failure("notify/send_email", "GMAIL_ADDRESS or GMAIL_APP_PASSWORD not set — skipping email")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = address
    msg["To"] = recipient
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    if html_body:
        msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context, timeout=30) as server:
            server.login(address, password)
            server.sendmail(address, [recipient], msg.as_string())
        log.info("Email sent to %s", recipient)
        return True
    except Exception as e:  # noqa: BLE001
        record_failure("notify/send_email", e)
        return False


def summary_to_html(text_summary: str, dashboard_url: str) -> str:
    """Wrap the plain-text summary in a minimal dark HTML email."""
    lines = text_summary.replace("{dashboard_url}", dashboard_url).splitlines()
    body = []
    for ln in lines:
        stripped = ln.strip()
        if not stripped:
            body.append("<br>")
        elif stripped.startswith(("▲", "▼", "•")):
            body.append(f'<div style="padding:4px 0">{_html_escape(stripped)}</div>')
        elif stripped.isupper() or stripped.startswith("WHAT CHANGED"):
            body.append(f'<div style="font-weight:600;color:#eda100;margin-top:10px">{_html_escape(stripped)}</div>')
        else:
            body.append(f'<div>{_html_escape(stripped)}</div>')
    return f"""<div style="background:#0d0d0d;color:#eee;font-family:system-ui,sans-serif;
padding:20px;border-radius:12px;max-width:600px">
<h2 style="margin:0 0 12px">📊 Weekly Market Dashboard</h2>
{''.join(body)}
<p style="margin-top:18px"><a href="{_html_escape(dashboard_url)}"
style="background:#3987e5;color:#fff;padding:10px 16px;border-radius:8px;
text-decoration:none;display:inline-block">Open full dashboard →</a></p>
<p style="color:#898781;font-size:12px;margin-top:16px">Not investment advice.</p>
</div>"""


def _html_escape(s: str) -> str:
    import html

    return html.escape(s)
