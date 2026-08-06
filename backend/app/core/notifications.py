"""
=============================================================================
VeriField Nexus — Email & Notification Service Architecture
=============================================================================
Provides clean event boundaries for transactional email notifications:
- USER_REGISTERED
- ACCOUNT_APPROVED
- ACCOUNT_REJECTED
- ACCOUNT_ACTIVATED
- PASSWORD_RESET_REQUESTED
- WELCOME_ONBOARDING

NOTE: Email delivery is explicitly DEFERRED until a production domain and
Resend sender identity are configured. When EMAIL_NOTIFICATIONS_ENABLED is false,
this service safely records an internal EMAIL_NOT_CONFIGURED status without
fabricating email delivery or throwing errors during auth workflows.
=============================================================================
"""

import logging
from enum import Enum
from typing import Any, Dict, Optional
from app.core.config import settings

logger = logging.getLogger("verifield.notifications")


class NotificationEvent(str, Enum):
    USER_REGISTERED = "USER_REGISTERED"
    ACCOUNT_APPROVED = "ACCOUNT_APPROVED"
    ACCOUNT_REJECTED = "ACCOUNT_REJECTED"
    ACCOUNT_ACTIVATED = "ACCOUNT_ACTIVATED"
    PASSWORD_RESET_REQUESTED = "PASSWORD_RESET_REQUESTED"
    WELCOME_ONBOARDING = "WELCOME_ONBOARDING"


class EmailService:
    """
    Production-ready email service abstraction prepared for future Resend integration.
    Never emails plaintext passwords or logs credentials.
    """

    def __init__(self):
        self.enabled = getattr(settings, "email_notifications_enabled", False)
        self.api_key = getattr(settings, "resend_api_key", "")
        self.from_email = getattr(settings, "resend_from_email", "")
        self.from_name = getattr(settings, "resend_from_name", "VeriField Nexus")

    async def dispatch_event_notification(
        self,
        event: NotificationEvent,
        recipient_email: str,
        recipient_name: Optional[str] = None,
        context_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Dispatches notification event. If email notifications are not enabled
        (production domain pending), returns internal EMAIL_NOT_CONFIGURED state.
        Never fabricates an EMAIL_SENT state.
        """
        if not self.enabled or not self.api_key or not self.from_email:
            logger.info(
                f"Notification event '{event.value}' triggered for recipient, "
                "but email delivery is deferred (EMAIL_NOT_CONFIGURED)."
            )
            return {
                "status": "EMAIL_NOT_CONFIGURED",
                "event": event.value,
                "recipient": recipient_email,
                "detail": "Email delivery deferred pending production domain configuration.",
            }

        # Future Resend API HTTP dispatch logic goes here when production domain is verified.
        return {
            "status": "EMAIL_NOT_CONFIGURED",
            "event": event.value,
            "recipient": recipient_email,
            "detail": "Resend API dispatch pending production domain sender verification.",
        }


email_service = EmailService()
