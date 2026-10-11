"""
SecureIoT-X — Telegram Bot Notification Service.

Sends real-time security alerts via Telegram Bot API for HIGH/CRITICAL events.
Configuration via environment variables only — token is NEVER hardcoded.

Required env vars:
    TELEGRAM_BOT_TOKEN  — Bot token from @BotFather
    TELEGRAM_CHAT_ID    — Target chat/group/channel ID

Telegram is ONLY a notification channel.
It does NOT replace MongoDB or Ganache.
It does NOT store security events.
Telegram failure DOES NOT roll back MongoDB or Ganache records.
"""

import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger("secureiot.telegram")


def _get_token() -> str:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        try:
            from backend.core.config import settings
            token = getattr(settings, "telegram_bot_token", "") or ""
        except Exception:
            pass
    return token


def _get_chat_id() -> str:
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not chat_id:
        try:
            from backend.core.config import settings
            chat_id = getattr(settings, "telegram_chat_id", "") or ""
        except Exception:
            pass
    return str(chat_id)


def is_configured() -> bool:
    """Check if Telegram credentials are set in environment."""
    return bool(_get_token() and _get_chat_id())


def _esc(text: str) -> str:
    """Escape all MarkdownV2 special characters in a string."""
    special = r"\_*[]()~`>#+-=|{}.!"
    return re.sub(r"([" + re.escape(special) + r"])", r"\\\1", str(text))


async def send_security_alert(
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
    Send a formatted security alert to Telegram.

    Non-fatal: always returns a dict, never raises.
    Returns:
        {"sent": True, "message_id": ...}  on success
        {"sent": False, "error": ..., "reason": ...}  on failure / not configured
    """
    token = _get_token()
    chat_id = _get_chat_id()

    if not token or not chat_id:
        logger.warning(
            "Telegram notification skipped — TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set. "
            "Add them to .env to enable alerts."
        )
        return {"sent": False, "reason": "TELEGRAM_NOT_CONFIGURED"}

    try:
        import httpx

        ts = timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        if severity == "CRITICAL":
            sev_emoji = "🚨🚨"
        elif severity == "HIGH":
            sev_emoji = "⚠️"
        else:
            sev_emoji = "ℹ️"

        device_status = "🔴 ISOLATED" if is_isolated else "🟡 ONLINE"

        blockchain_section = ""
        if tx_hash:
            blockchain_section = (
                f"\n\n🔗 *Blockchain:*\n"
                f"Network: `Ganache`\n"
                f"Tx: `{_esc(tx_hash)}`"
            )
            if block_number is not None:
                blockchain_section += f"\nBlock: `\\#{_esc(str(block_number))}`"
        else:
            blockchain_section = "\n\n🔗 *Blockchain:* `Ganache not connected`"

        message = (
            f"{sev_emoji} *SECUREIOT\\-X SECURITY ALERT* {sev_emoji}\n\n"
            f"🖥 *Device:* `{_esc(device_id)}`\n"
            f"💥 *Attack:* `{_esc(attack_type)}`\n"
            f"🤖 *Prediction:* `{_esc(prediction)}`\n\n"
            f"📊 *Risk Score:* `{_esc(str(round(risk_score, 2)))}`\n"
            f"🔥 *Severity:* `{_esc(severity)}`\n\n"
            f"🛡 *Response:* `{_esc(action)}`\n"
            f"📡 *Status:* {device_status}\n\n"
            f"🆔 *Event ID:*\n`{_esc(event_id)}`"
            f"{blockchain_section}\n\n"
            f"🕐 *Time:*\n`{_esc(ts)}`"
        )

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "MarkdownV2",
        }

        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(url, json=payload)

        data = resp.json()
        if data.get("ok"):
            msg_id = data.get("result", {}).get("message_id")
            logger.info(
                "Telegram alert sent: event=%s device=%s severity=%s msg_id=%s",
                event_id, device_id, severity, msg_id,
            )
            return {"sent": True, "message_id": msg_id}
        else:
            err = data.get("description", "Unknown Telegram API error")
            logger.error("Telegram API returned error for event %s: %s", event_id, err)
            # Fallback: retry as plain text
            return await _send_plain_fallback(token, chat_id, event_id, device_id, attack_type,
                                              risk_score, severity, action, is_isolated, tx_hash, ts)

    except Exception as exc:
        err_msg = str(exc) or type(exc).__name__
        logger.error(
            "Telegram notification FAILED for event %s (device=%s severity=%s): %s",
            event_id, device_id, severity, err_msg,
        )
        return {"sent": False, "error": err_msg}


async def _send_plain_fallback(
    token: str, chat_id: str,
    event_id: str, device_id: str, attack_type: str,
    risk_score: float, severity: str, action: str, is_isolated: bool,
    tx_hash: Optional[str], ts: str,
) -> Dict[str, Any]:
    """Send plain-text alert as fallback if MarkdownV2 fails."""
    try:
        import httpx
        status = "ISOLATED" if is_isolated else "ONLINE"
        text = (
            f"SECUREIOT-X {severity} ALERT\n"
            f"Device: {device_id}\n"
            f"Attack: {attack_type}\n"
            f"Risk: {round(risk_score, 2)}\n"
            f"Action: {action}\n"
            f"Status: {status}\n"
            f"Event: {event_id}\n"
            f"TX: {tx_hash or 'N/A'}\n"
            f"Time: {ts}"
        )
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(url, json={"chat_id": chat_id, "text": text})
        data = resp.json()
        if data.get("ok"):
            logger.info("Telegram plain-text fallback sent for event %s", event_id)
            return {"sent": True, "message_id": data.get("result", {}).get("message_id"), "mode": "plain"}
        return {"sent": False, "error": data.get("description", "Fallback also failed")}
    except Exception as exc:
        return {"sent": False, "error": str(exc)}


async def test_telegram_connection() -> Dict[str, Any]:
    """Test if Telegram credentials are valid by calling getMe API."""
    token = _get_token()
    if not token:
        return {"ok": False, "reason": "TELEGRAM_BOT_TOKEN not set"}

    try:
        import httpx
        url = f"https://api.telegram.org/bot{token}/getMe"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
        data = resp.json()
        if data.get("ok"):
            bot = data.get("result", {})
            return {
                "ok": True,
                "bot_username": bot.get("username"),
                "bot_name": bot.get("first_name"),
                "chat_id_configured": bool(_get_chat_id()),
            }
        return {"ok": False, "error": data.get("description")}
    except Exception as e:
        return {"ok": False, "error": str(e)}
