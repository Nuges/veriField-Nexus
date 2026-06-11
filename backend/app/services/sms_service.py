"""
=============================================================================
VeriField Nexus — Twilio SMS Service
=============================================================================
Provides production-ready functions for:
- Dispatching outbound SMS messages using Twilio REST API
- Verifying incoming Twilio webhook signatures (HMAC-SHA1 verification)
=============================================================================
"""

import hmac
import hashlib
import base64
import logging
import httpx
from typing import Dict, Any

from app.core.config import settings

logger = logging.getLogger("verifield.services.sms")


async def send_twilio_sms(to_phone: str, body: str) -> bool:
    """
    Sends an SMS message using Twilio's REST API.
    If credentials are missing, falls back to logging the message to the console.
    
    Args:
        to_phone: The recipient's E.164 phone number (e.g. "+1234567890").
        body: The text content of the message.
        
    Returns:
        bool: True if sent successfully (or fallback succeeded), False on API error.
    """
    sid = settings.twilio_account_sid
    token = settings.twilio_auth_token
    from_phone = settings.twilio_phone_number

    if not sid or not token or not from_phone:
        logger.warning(
            f"Twilio SMS credentials missing from environment. console-fallback mode active. "
            f"To: {to_phone} | Message: {body}"
        )
        # In development/sandbox dry-run mode, return True to prevent breaking client flow
        return True

    url = f"https://api.twilio.org/2010-04-01/Accounts/{sid}/Messages.json"
    auth = (sid, token)
    data = {
        "To": to_phone,
        "From": from_phone,
        "Body": body,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, auth=auth, data=data)
            if response.status_code in (200, 201):
                logger.info(f"SMS successfully sent via Twilio to {to_phone}")
                return True
            else:
                logger.error(
                    f"Failed to send Twilio SMS. Code: {response.status_code} | "
                    f"Response: {response.text}"
                )
                return False
    except Exception as e:
        logger.error(f"HTTP exception occurred when calling Twilio: {e}")
        return False


def verify_twilio_signature(url: str, params: Dict[str, Any], signature: str) -> bool:
    """
    Verifies that an incoming POST webhook request originated from Twilio.
    Ref: https://www.twilio.com/docs/usage/security#validating-requests
    
    Args:
        url: The full target URL of the webhook (matching Twilio config exactly).
        params: The form parameters from the POST body.
        signature: The X-Twilio-Signature header value.
        
    Returns:
        bool: True if request signature is valid, False otherwise.
    """
    if not settings.twilio_validate_signature:
        logger.warning("Twilio signature validation bypassed via configuration.")
        return True

    token = settings.twilio_auth_token
    if not token:
        logger.error("Cannot validate Twilio signature: twilio_auth_token is not set.")
        return False

    if not signature:
        logger.warning("Twilio request signature validation failed: X-Twilio-Signature header is missing.")
        return False

    # 1. Concatenate URL and sorted post params key-values (no separators)
    s = url
    for key in sorted(params.keys()):
        s += key + str(params[key])

    # 2. Compute HMAC-SHA1 of string using Twilio Auth Token as secret key
    try:
        key_bytes = token.encode("utf-8")
        msg_bytes = s.encode("utf-8")
        
        computed_hmac = hmac.new(key_bytes, msg_bytes, hashlib.sha1).digest()
        computed_sig = base64.b64encode(computed_hmac).decode("utf-8")
        
        # 3. Securely compare computed signature against the Twilio signature header
        return hmac.compare_digest(computed_sig, signature)
    except Exception as e:
        logger.error(f"Error computing request signature verification: {e}")
        return False
