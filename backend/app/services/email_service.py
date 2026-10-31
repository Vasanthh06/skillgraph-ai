"""Server-only provider boundary. Never log request bodies or provider response bodies."""
import httpx
from app.core.config import get_settings


class EmailUnavailable(Exception):
    pass


def send_email(to: str, subject: str, html: str, key: str) -> str:
    s = get_settings()
    if not s.RESEND_API_KEY or not s.EMAIL_FROM:
        raise EmailUnavailable("Email is not configured")
    try:
        with httpx.Client(timeout=12) as client:
            response = client.post("https://api.resend.com/emails", headers={
                "Authorization": f"Bearer {s.RESEND_API_KEY}", "Idempotency-Key": key,
            }, json={"from": s.EMAIL_FROM, "to": [to], "subject": subject, "html": html})
        response.raise_for_status()
        return str(response.json()["id"])[:120]
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        raise EmailUnavailable("Email provider unavailable; try later") from None
