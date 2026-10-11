"""
SecureIoT-X — Email Notification Service.

Sends real-time security alert emails via SMTP (Gmail or any provider)
for HIGH/CRITICAL security events.

Configuration via environment variables only:
    SMTP_HOST        — SMTP server host (e.g. smtp.gmail.com)
    SMTP_PORT        — SMTP port (587 for STARTTLS, 465 for SSL)
    SMTP_USERNAME    — Login username / sender address
    SMTP_PASSWORD    — Login password or app password
    SMTP_FROM        — From address (defaults to SMTP_USERNAME)
    SMTP_TO          — Recipient email (defaults to SMTP_USERNAME if not set)

Email is ONLY a notification channel.
Email failure does NOT roll back MongoDB or Ganache records.
"""

import logging
import os
import smtplib
import ssl
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, Optional

logger = logging.getLogger("secureiot.email")


def _cfg(key: str, fallback: str = "") -> str:
    return os.environ.get(key, "") or fallback


def _is_gmail() -> bool:
    return "gmail" in _cfg("SMTP_HOST").lower()


def _looks_like_app_password(pwd: str) -> bool:
    """Gmail App Passwords are 16 chars (no spaces) or 19 chars (with spaces like 'abcd efgh ijkl mnop')."""
    clean = pwd.replace(" ", "")
    return len(clean) == 16


def is_configured() -> bool:
    """Return True if SMTP credentials are set in environment."""
    return bool(_cfg("SMTP_HOST") and _cfg("SMTP_USERNAME") and _cfg("SMTP_PASSWORD"))


def _build_html(
    event_id: str,
    device_id: str,
    attack_type: str,
    prediction: str,
    risk_score: float,
    severity: str,
    action: str,
    is_isolated: bool,
    tx_hash: Optional[str],
    block_number: Optional[int],
    timestamp: str,
) -> str:
    sev_color = {"CRITICAL": "#c0392b", "HIGH": "#e67e22", "MEDIUM": "#f1c40f", "LOW": "#27ae60"}.get(severity, "#888")
    device_status = "🔴 ISOLATED" if is_isolated else "🟡 ONLINE"
    blockchain_row = ""
    if tx_hash:
        blockchain_row = f"""
        <tr><td><b>Ganache TX</b></td><td><code style="font-size:11px">{tx_hash}</code></td></tr>
        <tr><td><b>Block</b></td><td>#{block_number}</td></tr>
        """

    return f"""
    <html><body style="font-family:Arial,sans-serif;background:#1a1a2e;color:#eee;padding:20px">
    <div style="max-width:600px;margin:auto;background:#16213e;border-radius:12px;overflow:hidden">
      <div style="background:{sev_color};padding:20px;text-align:center">
        <h1 style="margin:0;color:#fff;font-size:22px">🚨 SECUREIOT-X SECURITY ALERT 🚨</h1>
        <p style="margin:6px 0 0;color:#ffffffcc;font-size:14px">Severity: <b>{severity}</b></p>
      </div>
      <div style="padding:24px">
        <table style="width:100%;border-collapse:collapse;color:#ddd;font-size:14px">
          <tr><td style="padding:8px 0;width:140px"><b>Device</b></td><td>{device_id}</td></tr>
          <tr><td style="padding:8px 0"><b>Attack Type</b></td><td>{attack_type}</td></tr>
          <tr><td style="padding:8px 0"><b>AI Prediction</b></td><td>{prediction}</td></tr>
          <tr><td style="padding:8px 0"><b>Risk Score</b></td><td><span style="color:{sev_color};font-weight:bold">{risk_score}</span></td></tr>
          <tr><td style="padding:8px 0"><b>Severity</b></td><td><span style="color:{sev_color};font-weight:bold">{severity}</span></td></tr>
          <tr><td style="padding:8px 0"><b>Response Action</b></td><td>{action}</td></tr>
          <tr><td style="padding:8px 0"><b>Device Status</b></td><td>{device_status}</td></tr>
          <tr><td style="padding:8px 0"><b>Event ID</b></td><td><code>{event_id}</code></td></tr>
          {blockchain_row}
          <tr><td style="padding:8px 0"><b>Time</b></td><td>{timestamp}</td></tr>
        </table>
      </div>
      <div style="background:#0f3460;padding:12px 24px;font-size:11px;color:#aaa;text-align:center">
        SecureIoT-X Automated Security Alert System
      </div>
    </div>
    </body></html>
    """


async def send_email_alert(
    event_id: str,
    device_id: str,
    attack_type: str,
    prediction: str,
    risk_score: float,
    severity: str,
    action: str,
    is_isolated: bool,
    tx_hash: Optional[str] = None,
    block_number: Optional[int] = None,
    timestamp: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Send a formatted HTML security alert email.

    Non-fatal: always returns a dict, never raises.
    Returns:
        {"sent": True}  on success
        {"sent": False, "reason": ..., "error": ...}  on failure
    """
    if not is_configured():
        logger.warning("Email notification skipped — SMTP_HOST/USERNAME/PASSWORD not fully set.")
        return {"sent": False, "reason": "EMAIL_NOT_CONFIGURED"}

    # Warn if Gmail is configured with a regular password (not App Password)
    password_check = _cfg("SMTP_PASSWORD")
    if _is_gmail() and not _looks_like_app_password(password_check):
        logger.warning(
            "Gmail SMTP requires an App Password (16 chars), not your regular password. "
            "Generate one at: https://myaccount.google.com/apppasswords"
        )

    smtp_host = _cfg("SMTP_HOST")
    smtp_port = int(_cfg("SMTP_PORT", "587"))
    username = _cfg("SMTP_USERNAME")
    password = _cfg("SMTP_PASSWORD")
    from_addr = _cfg("SMTP_FROM") or username
    to_addr = _cfg("SMTP_TO") or username  # send to self if no SMTP_TO

    ts = timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    subject = f"[SecureIoT-X] {severity} ALERT — {attack_type} on {device_id}"

    html_body = _build_html(
        event_id=event_id,
        device_id=device_id,
        attack_type=attack_type,
        prediction=prediction,
        risk_score=round(risk_score, 2),
        severity=severity,
        action=action,
        is_isolated=is_isolated,
        tx_hash=tx_hash,
        block_number=block_number,
        timestamp=ts,
    )

    plain_body = (
        f"SECUREIOT-X SECURITY ALERT\n"
        f"Severity: {severity}\n"
        f"Device: {device_id}\n"
        f"Attack: {attack_type}\n"
        f"Prediction: {prediction}\n"
        f"Risk Score: {risk_score}\n"
        f"Response: {action}\n"
        f"Event ID: {event_id}\n"
        f"TX Hash: {tx_hash or 'N/A'}\n"
        f"Time: {ts}\n"
    )

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = to_addr
        msg.attach(MIMEText(plain_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        # Send in thread executor to avoid blocking async event loop
        import asyncio
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _send_smtp, smtp_host, smtp_port, username, password, from_addr, to_addr, msg)

        logger.info(
            "Email alert sent: event=%s device=%s severity=%s to=%s",
            event_id, device_id, severity, to_addr,
        )
        return {"sent": True, "recipient": to_addr}

    except Exception as exc:
        err_msg = str(exc) or type(exc).__name__
        # Detect Gmail App Password issue specifically
        gmail_hint = ""
        if _is_gmail() and "Connection unexpectedly closed" in err_msg:
            gmail_hint = " [Gmail requires 16-char App Password — go to myaccount.google.com/apppasswords]"
        elif _is_gmail() and ("Authentication" in err_msg or "Username and Password" in err_msg or "BadCredentials" in err_msg):
            gmail_hint = " [Gmail requires App Password — go to myaccount.google.com/apppasswords]"
        logger.error(
            "Email notification FAILED for event %s (device=%s severity=%s): %s%s",
            event_id, device_id, severity, err_msg, gmail_hint,
        )
        return {"sent": False, "error": err_msg + gmail_hint}


def _send_smtp(host: str, port: int, username: str, password: str, from_addr: str, to_addr: str, msg: MIMEMultipart) -> None:
    """Blocking SMTP send — called in thread executor."""
    context = ssl.create_default_context()
    if port == 465:
        # SSL
        with smtplib.SMTP_SSL(host, port, context=context, timeout=20) as server:
            server.login(username, password)
            server.sendmail(from_addr, to_addr, msg.as_string())
    else:
        # STARTTLS (587)
        with smtplib.SMTP(host, port, timeout=20) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(username, password)
            server.sendmail(from_addr, to_addr, msg.as_string())
