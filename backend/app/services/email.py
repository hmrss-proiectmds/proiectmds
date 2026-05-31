"""
Email notification service.

Sends moderation alerts to agent owners when an admin takes action.
Uses stdlib smtplib via asyncio.to_thread so it doesn't block the event loop.

When SMTP_HOST is empty the function logs the alert and returns without
sending — safe for dev/test environments with no mail server.
"""

import asyncio
import logging
import smtplib
from email.mime.text import MIMEText

from app.config import settings

log = logging.getLogger(__name__)

_ACTION_LABELS = {
    "pause": "paused",
    "ban": "permanently banned",
    "unpause": "unpaused (re-activated)",
}

_BODY_TEMPLATE = """\
Hello,

This is an automated alert from the AI Game Simulation Platform.

Your agent "{agent_name}" has been {action_label} by a platform administrator.

Reason: Administrative moderation action.

If you believe this was in error, please contact platform support.

— AI Game Simulation Platform
"""


def _send_sync(to_email: str, subject: str, body: str) -> None:
    """Blocking SMTP send — called via asyncio.to_thread."""
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_email

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as smtp:
        smtp.ehlo()
        if settings.SMTP_PORT == 587:
            smtp.starttls()
            smtp.ehlo()
        if settings.SMTP_USER:
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        smtp.sendmail(settings.SMTP_FROM, [to_email], msg.as_string())


async def send_moderation_alert(
    owner_email: str,
    agent_name: str,
    action: str,
) -> None:
    """
    Send a moderation alert email to an agent owner.

    Args:
        owner_email: Recipient address.
        agent_name:  Human-readable agent name.
        action:      One of "pause", "ban", "unpause".
    """
    action_label = _ACTION_LABELS.get(action, action)
    subject = f"[Platform Alert] Your agent '{agent_name}' has been {action_label}"
    body = _BODY_TEMPLATE.format(agent_name=agent_name, action_label=action_label)

    if not settings.SMTP_HOST:
        log.info(
            "[email] SMTP not configured — suppressing alert to %s (action=%s, agent=%s)",
            owner_email,
            action,
            agent_name,
        )
        return

    try:
        await asyncio.to_thread(_send_sync, owner_email, subject, body)
        log.info("[email] Moderation alert sent to %s for agent '%s' (%s)", owner_email, agent_name, action)
    except Exception as exc:
        log.error("[email] Failed to send alert to %s: %s", owner_email, exc)
