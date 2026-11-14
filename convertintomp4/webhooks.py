"""Verify deliveries sent to a job's ``webhook_url``."""

import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Union


def verify_job_webhook(
    raw_body: Union[bytes, str],
    signature: str,
    secret: str,
    tolerance_seconds: int = 300,
) -> bool:
    """Check ``X-ConvertIntoMP4-Signature`` (``sha256=<hex>``) over the raw body.

    Args:
        raw_body: The request body exactly as received, before JSON parsing.
        signature: The header value.
        secret: From ``client.get_job_webhook_secret()["secret"]``.
        tolerance_seconds: Reject events whose ``timestamp`` is older than this
            (default 300). Pass 0 to skip the age check.
    """
    body = raw_body.encode("utf-8") if isinstance(raw_body, str) else raw_body
    expected = "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature or ""):
        return False
    if tolerance_seconds > 0:
        try:
            ts = json.loads(body.decode("utf-8")).get("timestamp")
            sent = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        except (ValueError, TypeError, AttributeError):
            return False
        if abs((datetime.now(timezone.utc) - sent).total_seconds()) > tolerance_seconds:
            return False
    return True
