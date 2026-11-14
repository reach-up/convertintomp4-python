"""Job webhook verification and the single Jobs API error shape."""

import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from convertintomp4 import Client, verify_job_webhook
from convertintomp4.exceptions import ApiError, AuthenticationError, RateLimitError

SECRET = "whsec_test"


def sign(body: str) -> str:
    return "sha256=" + hmac.new(SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()


def test_verify_accepts_fresh_signed_body_and_rejects_the_rest():
    body = json.dumps({"event": "job.finished", "timestamp": datetime.now(timezone.utc).isoformat()})
    assert verify_job_webhook(body, sign(body), SECRET)
    assert not verify_job_webhook(body + " ", sign(body), SECRET)
    assert not verify_job_webhook(body, sign(body), "other")
    stale = json.dumps({"event": "job.failed", "timestamp": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()})
    assert not verify_job_webhook(stale, sign(stale), SECRET)
    assert verify_job_webhook(stale, sign(stale), SECRET, tolerance_seconds=0)


def _response(status, body, headers=None):
    r = MagicMock()
    r.status_code = status
    r.ok = 200 <= status < 300
    r.json.return_value = body
    r.headers = headers or {}
    return r


def test_error_code_surfaces_from_the_single_shape():
    client = Client(api_key="k")
    r = _response(422, {"success": False, "error": {"code": "OPERATION_NOT_SUPPORTED", "message": "pdf/to-pdfa is not supported"}})
    with pytest.raises(ApiError) as e:
        client._handle_response(r)
    assert e.value.code == "OPERATION_NOT_SUPPORTED"


def test_quota_exceeded_is_not_a_rate_limit_retry():
    client = Client(api_key="k")
    r = _response(429, {"success": False, "error": {"code": "QUOTA_EXCEEDED", "message": "Daily limit reached"}})
    with pytest.raises(ApiError) as e:
        client._handle_response(r)
    assert not isinstance(e.value, RateLimitError)


def test_old_flat_error_shape_does_not_crash_the_parser():
    client = Client(api_key="k")
    with pytest.raises(AuthenticationError):
        client._handle_response(_response(401, {"error": "Authentication required", "code": "AUTH_REQUIRED"}))
