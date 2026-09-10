"""Notification service with provider abstraction (SMS, push, email, in-app)."""
from abc import ABC, abstractmethod
from typing import Optional

from app.core.config import settings


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
        self.api_key = settings.SMS_API_KEY

    def send(self, recipient, subject, message, **kwargs):
        if self.provider != "mock" and not self.api_key:
            return {"status": "failed", "error": "SMS_API_KEY not configured"}
        # Real integrations (Twilio, etc.) would call out here.
        return {"status": "sent", "provider": self.provider}


class EmailProvider(NotificationProvider):
    channel = "email"
    name = "mock_email"

    def send(self, recipient, subject, message, **kwargs):
        if not settings.EMAIL_API_KEY and "smtp" in (settings.EMAIL_FROM or ""):
            return {"status": "failed", "error": "EMAIL_API_KEY not configured"}
        return {"status": "sent", "provider": "mock_email"}


class PushProvider(NotificationProvider):
    channel = "push"
    name = "mock_push"

    def send(self, recipient, subject, message, **kwargs):
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
