import logging
import os
import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage

logger = logging.getLogger(__name__)


def send_meeting_invite_email(
    *,
    to_email: str,
    organizer_email: str,
    room_name: str,
    start_time: datetime,
    end_time: datetime,
) -> None:
    """Отправляет приглашение на встречу. Если SMTP_HOST не задан — только логирует."""
    host = os.getenv("SMTP_HOST", "").strip()
    if not host:
        logger.info(
            "SMTP_HOST not configured; skipping email to %s (meeting invite would be sent in production)",
            to_email,
        )
        return

    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASSWORD", "")
    mail_from = os.getenv("SMTP_FROM", user or "noreply@localhost")
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes")

    start_s = start_time.strftime("%Y-%m-%d %H:%M UTC")
    end_s = end_time.strftime("%Y-%m-%d %H:%M UTC")
    subject = f"Приглашение: переговорка «{room_name}» ({start_s})"
    body = (
        f"Вас добавили к встрече в переговорной.\n\n"
        f"Комната: {room_name}\n"
        f"Организатор: {organizer_email}\n"
        f"Начало: {start_s}\n"
        f"Окончание: {end_s}\n"
    )

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = mail_from
    msg["To"] = to_email
    msg.set_content(body)

    if use_tls:
        context = ssl.create_default_context()
        with smtplib.SMTP(host, port, timeout=30) as smtp:
            smtp.starttls(context=context)
            if user:
                smtp.login(user, password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=30) as smtp:
            if user:
                smtp.login(user, password)
            smtp.send_message(msg)
