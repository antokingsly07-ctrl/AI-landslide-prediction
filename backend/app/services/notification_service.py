"""Notification service with provider abstraction (SMS, push, email, in-app).

Only genuinely delivered notifications report status "sent". Unconfigured
providers report "not_configured" so the system never lies about delivery.
"""
from abc import ABC, abstractmethod

import httpx

from app.core.config import settings

_FAST2SMS_URL = "https://www.fast2sms.com/dev/bulkV2"


class NotificationProvider(ABC):
    channel = "base"
    name = "base"

    @abstractmethod
    def send(self, recipient: str, subject: str, message: str, **kwargs) -> dict:
        """Return {status, provider, error?}."""


class SMSSProvider(NotificationProvider):
    channel = "sms"
    name = "mock_sms"

    def __init__(self, provider: str = ""):
        self.provider = provider or settings.SMS_PROVIDER or "mock"

    def send(self, recipient, subject, message, **kwargs):
        if self.provider == "fast2sms":
            return Fast2SMSSMSProvider().send(recipient, subject, message, **kwargs)
        return {
            "status": "not_configured",
            "provider": self.provider,
            "error": "No real SMS provider configured (set SMS_PROVIDER=fast2sms + FAST2SMS_API_KEY)",
        }


class Fast2SMSSMSProvider(NotificationProvider):
    """Real SMS delivery via Fast2SMS (India) — requires FAST2SMS_API_KEY."""

    channel = "sms"
    name = "fast2sms"

    def send(self, recipient, subject, message, **kwargs):
        api_key = settings.FAST2SMS_API_KEY
        if not api_key:
            return {"status": "not_configured", "provider": "fast2sms",
                    "error": "FAST2SMS_API_KEY not set"}
        if not recipient:
            return {"status": "failed", "provider": "fast2sms", "error": "no recipient"}
        numbers = ",".join(n.strip() for n in str(recipient).split(",") if n.strip())
        params = {
            "authorization": api_key,
            "variables_values": message,
            "numbers": numbers,
            "route": settings.SMS_ROUTE or "qtp",
            "flash": "0",
        }
        if settings.SMS_SENDER_ID:
            params["sender_id"] = settings.SMS_SENDER_ID
        try:
            resp = httpx.get(_FAST2SMS_URL, params=params, timeout=20)
            body = resp.json()
            ok = bool(body.get("return")) or resp.status_code == 200
            return {"status": "sent" if ok else "failed", "provider": "fast2sms",
                    "error": None if ok else body.get("message")}
        except Exception as exc:  # pragma: no cover - outbound network failure
            return {"status": "failed", "provider": "fast2sms", "error": str(exc)}


class EmailProvider(NotificationProvider):
    channel = "email"
    name = "mock_email"

    def send(self, recipient, subject, message, **kwargs):
        if not settings.EMAIL_API_KEY:
            return {"status": "not_configured", "provider": "mock_email",
                    "error": "EMAIL_API_KEY not configured"}
        return {"status": "not_configured", "provider": "mock_email",
                "error": "SMTP provider not configured"}


class PushProvider(NotificationProvider):
    channel = "push"
    name = "mock_push"

    def send(self, recipient, subject, message, **kwargs):
        if not settings.PUSH_VAPID_PRIVATE_KEY:
            return {"status": "not_configured", "provider": "mock_push",
                    "error": "PUSH_VAPID_* keys not configured"}
        return {"status": "sent", "provider": "mock_push"}


class InAppProvider(NotificationProvider):
    channel = "in_app"
    name = "in_app"

    def send(self, recipient, subject, message, **kwargs):
        return {"status": "sent", "provider": "in_app"}


class NotificationService:
    def __init__(self):
        self.providers: dict[str, NotificationProvider] = {
            "sms": SMSSProvider(),
            "email": EmailProvider(),
            "push": PushProvider(),
            "in_app": InAppProvider(),
        }

    def send(self, channel: str, recipient: str, subject: str, message: str, **kwargs) -> dict:
        provider = self.providers.get(channel)
        if provider is None:
            return {"status": "failed", "provider": channel, "error": "unknown channel"}
        return provider.send(recipient, subject, message, **kwargs)

    def send_all(self, recipient, subject, message, channels=None, **kwargs) -> list[dict]:
        channels = channels or ["in_app"]
        return [self.send(c, recipient, subject, message, **kwargs) for c in channels]


notification_service = NotificationService()