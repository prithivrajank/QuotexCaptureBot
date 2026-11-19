"""Optional Telegram alerts for newly-created CALL/PUT signals.

The notifier is disabled unless both Telegram environment variables are configured.
It never places trades and never logs the bot token.
"""
import logging
import os
import requests

logger = logging.getLogger(__name__)


def send_signal_alert(signal: dict) -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return False

    direction = str(signal.get("direction", "WAIT")).upper()
    if direction not in ("CALL", "PUT"):
        return False

    symbol = str(signal.get("symbol", "UNKNOWN"))
    timeframe = int(signal.get("timeframe_seconds", 60))
    expiry = signal.get("suggested_expiry_minutes")
    confidence = float(signal.get("confidence", 0))
    reasons = signal.get("reasons") or []
    timestamp = int(signal.get("timestamp", 0))

    # Telegram text is plain text; keep content bounded and escape no user-controlled HTML.
    lines = [
        f"QuotexCaptureBot | {direction}",
        f"Pair: {symbol}",
        f"Chart timeframe: {timeframe}s",
        f"Suggested expiry: {expiry} min" if expiry else "Suggested expiry: not set",
        f"Rule score: {confidence:.3f} (not win probability)",
        f"Candle timestamp: {timestamp}",
        "Data: visual estimate, not exchange-verified",
        "Reasons:",
    ]
    lines.extend(f"- {str(reason)[:180]}" for reason in reasons[:6])
    lines.append("Demo observation only. No trade was placed.")
    message = "\n".join(lines)[:3800]

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message, "disable_web_page_preview": True},
            timeout=8,
        )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("ok"):
            logger.warning("Telegram API rejected a signal notification")
            return False
        return True
    except (requests.RequestException, ValueError) as exc:
        logger.warning("Telegram signal notification failed: %s", type(exc).__name__)
        return False
