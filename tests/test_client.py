"""Tests for the ConvertIntoMP4 Python SDK client."""

import json
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
import requests

from convertintomp4.client import Client, DEFAULT_BASE_URL
from convertintomp4.exceptions import (
    ApiError,
    AuthenticationError,
    ConvertIntoMP4Error,
    NotFoundError,
    RateLimitError,
    TimeoutError,
    ValidationError,
)


# =========================================================================
# Initialization Tests
# =========================================================================


class TestClientInit:
    def test_requires_api_key(self):
        with pytest.raises(ConvertIntoMP4Error, match="API key is required"):
            Client(api_key="")

    def test_default_base_url(self):
        client = Client(api_key="test-key")
        assert client.base_url == DEFAULT_BASE_URL

    def test_custom_base_url(self):
        client = Client(api_key="test-key", base_url="https://custom.api.com/v1")
        assert client.base_url == "https://custom.api.com/v1"

    def test_sandbox_mode(self):
        client = Client(api_key="test-key", sandbox=True)
        assert client.base_url == DEFAULT_BASE_URL
        assert client._session.headers["X-Sandbox"] == "true"

    def test_sandbox_keeps_custom_base_url(self):
        client = Client(api_key="test-key", base_url="https://custom.api.com/v1", sandbox=True)
        assert client.base_url == "https://custom.api.com/v1"

    def test_no_sandbox_header_by_default(self):
        client = Client(api_key="test-key")
        assert "X-Sandbox" not in client._session.headers

    def test_default_timeout(self):
        client = Client(api_key="test-key")
        assert client.timeout == 30

    def test_custom_timeout(self):
        client = Client(api_key="test-key", timeout=60)
        assert client.timeout == 60

    def test_auth_header_set(self):
        client = Client(api_key="my-secret-key")
        assert client._session.headers["Authorization"] == "Bearer my-secret-key"

    def test_user_agent_header_set(self):
        client = Client(api_key="test-key")
        assert client._session.headers["User-Agent"] == "convertintomp4-python/1.0.0"

    def test_content_type_header_set(self):
        client = Client(api_key="test-key")
        assert client._session.headers["Content-Type"] == "application/json"

    def test_custom_headers_merged(self):
        client = Client(api_key="test-key", headers={"X-Custom": "value"})
        assert client._session.headers["X-Custom"] == "value"
        assert client._session.headers["Authorization"] == "Bearer test-key"

    def test_context_manager(self):
        with Client(api_key="test-key") as client:
            assert client.api_key == "test-key"


# =========================================================================
# Request Building & Job Methods Tests
# =========================================================================


def _mock_response(status_code=200, json_data=None, headers=None, content=b""):
    """Create a mock requests.Response object."""
    mock_resp = MagicMock(spec=requests.Response)
    mock_resp.status_code = status_code
    mock_resp.ok = 200 <= status_code < 300
    mock_resp.headers = headers or {}
    mock_resp.content = content

    if json_data is not None:
        mock_resp.json.return_value = json_data
    else:
        mock_resp.json.side_effect = ValueError("No JSON")

    return mock_resp


class TestJobMethods:
    @patch.object(requests.Session, "request")
    def test_create_job_sends_post(self, mock_request):
        job_data = {
            "id": "job-123",
            "status": "pending",
            "tasks": {},
            "created_at": "2026-01-01T00:00:00Z",
        }
        mock_request.return_value = _mock_response(200, {"data": job_data})

        client = Client(api_key="test-key")
        job = client.create_job({"tasks": {"convert": {"operation": "convert"}}})

        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        assert kwargs["method"] == "POST"
        assert kwargs["url"].endswith("/jobs")
        assert kwargs["json"] == {"tasks": {"convert": {"operation": "convert"}}}
        assert job.id == "job-123"
        assert job.status == "pending"

    @patch.object(requests.Session, "request")
    def test_get_job_sends_get(self, mock_request):
        job_data = {
            "id": "job-456",
            "status": "completed",
            "tasks": {},
            "created_at": "2026-01-01T00:00:00Z",
        }
        mock_request.return_value = _mock_response(200, {"data": job_data})

        client = Client(api_key="test-key")
        job = client.get_job("job-456")

        args, kwargs = mock_request.call_args
        assert kwargs["method"] == "GET"
        assert "/jobs/job-456" in kwargs["url"]
        assert job.id == "job-456"
        assert job.status == "completed"

    @patch.object(requests.Session, "request")
    def test_list_jobs_with_filters(self, mock_request):
        mock_request.return_value = _mock_response(200, {
            "data": {"data": [], "meta": {"total": 0}},
        })

        client = Client(api_key="test-key")
        client.list_jobs(status="completed", tag="batch-1", limit=10, offset=5)

        args, kwargs = mock_request.call_args
        assert kwargs["method"] == "GET"
        assert kwargs["params"]["status"] == "completed"
        assert kwargs["params"]["tag"] == "batch-1"
        assert kwargs["params"]["limit"] == 10
        assert kwargs["params"]["offset"] == 5

    @patch.object(requests.Session, "request")
    def test_delete_job_sends_delete(self, mock_request):
        mock_request.return_value = _mock_response(204)

        client = Client(api_key="test-key")
        result = client.delete_job("job-789")

        args, kwargs = mock_request.call_args
        assert kwargs["method"] == "DELETE"
        assert "/jobs/job-789" in kwargs["url"]
        assert result is None

    @patch.object(requests.Session, "request")
    def test_cancel_job_sends_post_to_cancel(self, mock_request):
        job_data = {
            "id": "job-abc",
            "status": "cancelled",
            "tasks": {},
            "created_at": "2026-01-01T00:00:00Z",
        }
        mock_request.return_value = _mock_response(200, {"data": job_data})

        client = Client(api_key="test-key")
        job = client.cancel_job("job-abc")

        args, kwargs = mock_request.call_args
        assert "/jobs/job-abc/cancel" in kwargs["url"]
        assert job.status == "cancelled"

    @patch.object(requests.Session, "request")
    def test_retry_job_sends_post_to_retry(self, mock_request):
        job_data = {
            "id": "job-def",
            "status": "pending",
            "tasks": {},
            "created_at": "2026-01-01T00:00:00Z",
        }
        mock_request.return_value = _mock_response(200, {"data": job_data})

        client = Client(api_key="test-key")
        job = client.retry_job("job-def")

        args, kwargs = mock_request.call_args
        assert "/jobs/job-def/retry" in kwargs["url"]


# =========================================================================
# Format Methods Tests
# =========================================================================


class TestFormatMethods:
    @patch.object(requests.Session, "request")
    def test_list_formats(self, mock_request):
        formats_data = [
            {"id": "mp4", "name": "MP4", "category": "video", "extension": ".mp4", "mime_types": ["video/mp4"]},
            {"id": "webm", "name": "WebM", "category": "video", "extension": ".webm", "mime_types": ["video/webm"]},
        ]
        mock_request.return_value = _mock_response(200, {"data": formats_data})

        client = Client(api_key="test-key")
        formats = client.list_formats()

        assert len(formats) == 2
        assert formats[0].id == "mp4"
        assert formats[1].id == "webm"

    @patch.object(requests.Session, "request")
    def test_list_formats_with_category(self, mock_request):
        mock_request.return_value = _mock_response(200, {"data": []})

        client = Client(api_key="test-key")
        client.list_formats(category="audio")

        args, kwargs = mock_request.call_args
        assert kwargs["params"]["category"] == "audio"

    @patch.object(requests.Session, "request")
    def test_get_format(self, mock_request):
        format_data = {
            "id": "mp4",
            "name": "MP4",
            "category": "video",
            "extension": ".mp4",
            "mime_types": ["video/mp4"],
        }
        mock_request.return_value = _mock_response(200, {"data": format_data})

        client = Client(api_key="test-key")
        fmt = client.get_format("mp4")

        assert fmt.id == "mp4"
        assert fmt.name == "MP4"

    @patch.object(requests.Session, "request")
    def test_get_format_options(self, mock_request):
        options_data = {
            "input_format": "mp4",
            "output_format": "webm",
            "options": [],
        }
        mock_request.return_value = _mock_response(200, {"data": options_data})

        client = Client(api_key="test-key")
        result = client.get_format_options("mp4", "webm")

        args, kwargs = mock_request.call_args
        assert kwargs["params"]["input_format"] == "mp4"
        assert kwargs["params"]["output_format"] == "webm"


# =========================================================================
# Webhook Methods Tests
# =========================================================================


class TestWebhookMethods:
    @patch.object(requests.Session, "request")
    def test_create_webhook(self, mock_request):
        webhook_data = {
            "id": "wh-123",
            "url": "https://example.com/hook",
            "events": ["job.completed"],
            "active": True,
            "created_at": "2026-01-01T00:00:00Z",
        }
        mock_request.return_value = _mock_response(200, {"data": webhook_data})

        client = Client(api_key="test-key")
        webhook = client.create_webhook(
            url="https://example.com/hook",
            events=["job.completed"],
            secret="my-secret",
        )

        args, kwargs = mock_request.call_args
        body = kwargs["json"]
        assert body["url"] == "https://example.com/hook"
        assert body["events"] == ["job.completed"]
        assert body["secret"] == "my-secret"
        assert webhook.id == "wh-123"

    @patch.object(requests.Session, "request")
    def test_list_webhooks(self, mock_request):
        webhooks_data = [
            {"id": "wh-1", "url": "https://a.com", "events": ["job.completed"], "active": True, "created_at": "2026-01-01T00:00:00Z"},
        ]
        mock_request.return_value = _mock_response(200, {"data": webhooks_data})

        client = Client(api_key="test-key")
        webhooks = client.list_webhooks()

        assert len(webhooks) == 1
        assert webhooks[0].id == "wh-1"

    @patch.object(requests.Session, "request")
    def test_delete_webhook(self, mock_request):
        mock_request.return_value = _mock_response(204)

        client = Client(api_key="test-key")
        result = client.delete_webhook("wh-123")

        args, kwargs = mock_request.call_args
        assert kwargs["method"] == "DELETE"
        assert "/webhooks/wh-123" in kwargs["url"]


# =========================================================================
# Convert / Import Methods Tests
# =========================================================================


class TestConvertMethods:
    @patch("convertintomp4.client.requests.post")
    def test_convert_uploads_multipart(self, mock_post):
        mock_post.return_value = _mock_response(200, {"jobId": "j-1", "status": "queued"})

        client = Client(api_key="test-key")
        result = client.convert(b"fake-file-data", "webm", filename="video.mp4")

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0].endswith("/convert")
        assert "files" in kwargs
        assert kwargs["data"]["targetFormat"] == "webm"

    @patch.object(requests.Session, "request")
    def test_import_from_url(self, mock_request):
        mock_request.return_value = _mock_response(200, {
            "data": {"jobId": "j-2", "status": "queued"},
        })

        client = Client(api_key="test-key")
        result = client.import_from_url(
            url="https://example.com/video.mp4",
            target_format="webm",
        )

        args, kwargs = mock_request.call_args
        assert kwargs["method"] == "POST"
        assert "/import/url" in kwargs["url"]
        assert kwargs["json"]["url"] == "https://example.com/video.mp4"
        assert kwargs["json"]["targetFormat"] == "webm"


# =========================================================================
# Error Handling Tests
# =========================================================================


class TestErrorHandling:
    @patch.object(requests.Session, "request")
    def test_401_raises_authentication_error(self, mock_request):
        mock_request.return_value = _mock_response(
            401,
            {"error": {"code": "AUTHENTICATION_ERROR", "message": "Invalid API key"}},
        )

        client = Client(api_key="bad-key")
        with pytest.raises(AuthenticationError) as exc_info:
            client.get_job("job-1")

        assert exc_info.value.status_code == 401

    @patch.object(requests.Session, "request")
    def test_404_raises_not_found_error(self, mock_request):
        mock_request.return_value = _mock_response(
            404,
            {"error": {"code": "NOT_FOUND", "message": "Job not found"}},
        )

        client = Client(api_key="test-key")
        with pytest.raises(NotFoundError):
            client.get_job("nonexistent")

    @patch.object(requests.Session, "request")
    def test_429_raises_rate_limit_error(self, mock_request):
        mock_request.return_value = _mock_response(
            429,
            {"error": {"code": "RATE_LIMIT_EXCEEDED", "message": "Too many requests"}},
            headers={"Retry-After": "30"},
        )

        client = Client(api_key="test-key")
        with pytest.raises(RateLimitError) as exc_info:
            client.list_jobs()

        assert exc_info.value.retry_after == 30

    @patch.object(requests.Session, "request")
    def test_400_raises_validation_error(self, mock_request):
        mock_request.return_value = _mock_response(
            400,
            {"error": {"code": "VALIDATION_ERROR", "message": "Invalid format", "details": {"field": "targetFormat"}}},
        )

        client = Client(api_key="test-key")
        with pytest.raises(ValidationError):
            client.create_job({"tasks": {}})

    @patch.object(requests.Session, "request")
    def test_500_raises_api_error(self, mock_request):
        mock_request.return_value = _mock_response(
            500,
            {"error": {"code": "INTERNAL_ERROR", "message": "Server error"}},
        )

        client = Client(api_key="test-key")
        with pytest.raises(ApiError) as exc_info:
            client.get_job("job-1")

        assert exc_info.value.status_code == 500
        assert exc_info.value.code == "INTERNAL_ERROR"


# =========================================================================
# Edge Case Tests
# =========================================================================


class TestEdgeCases:
    @patch.object(requests.Session, "request")
    def test_timeout_raises_timeout_error(self, mock_request):
        mock_request.side_effect = requests.exceptions.Timeout("Connection timed out")

        client = Client(api_key="test-key", timeout=5)
        with pytest.raises(TimeoutError):
            client.get_job("job-1")

    @patch.object(requests.Session, "request")
    def test_connection_error_raises_base_error(self, mock_request):
        mock_request.side_effect = requests.exceptions.ConnectionError("DNS lookup failed")

        client = Client(api_key="test-key")
        with pytest.raises(ConvertIntoMP4Error, match="Connection error"):
            client.get_job("job-1")

    @patch.object(requests.Session, "request")
    def test_non_json_successful_response_returns_content(self, mock_request):
        mock_resp = _mock_response(200, content=b"raw-binary-data")
        mock_resp.ok = True
        mock_resp.json.side_effect = ValueError("Not JSON")
        mock_request.return_value = mock_resp

        client = Client(api_key="test-key")
        result = client._request("GET", "/some-path")
        assert result == b"raw-binary-data"

    @patch.object(requests.Session, "request")
    def test_non_json_error_response_raises_api_error(self, mock_request):
        mock_resp = _mock_response(502, content=b"Bad Gateway")
        mock_resp.ok = False
        mock_resp.json.side_effect = ValueError("Not JSON")
        mock_request.return_value = mock_resp

        client = Client(api_key="test-key")
        with pytest.raises(ApiError) as exc_info:
            client._request("GET", "/some-path")

        assert exc_info.value.status_code == 502
        assert exc_info.value.code == "PARSE_ERROR"

    @patch.object(requests.Session, "request")
    def test_204_returns_none(self, mock_request):
        mock_request.return_value = _mock_response(204)

        client = Client(api_key="test-key")
        result = client._request("DELETE", "/jobs/j-1")
        assert result is None


# =========================================================================
# PDF Operations Tests
# =========================================================================


class TestPdfOperations:
    @patch.object(requests.Session, "request")
    def test_pdf_merge(self, mock_request):
        mock_request.return_value = _mock_response(200, {
            "data": {"url": "https://files.example.com/merged.pdf", "file_size": 1024},
        })

        client = Client(api_key="test-key")
        result = client.pdf_merge(["https://a.pdf", "https://b.pdf"])

        args, kwargs = mock_request.call_args
        assert kwargs["json"]["files"] == ["https://a.pdf", "https://b.pdf"]
        assert result.url == "https://files.example.com/merged.pdf"

    @patch.object(requests.Session, "request")
    def test_pdf_compress(self, mock_request):
        mock_request.return_value = _mock_response(200, {
            "data": {"url": "https://files.example.com/compressed.pdf", "file_size": 512},
        })

        client = Client(api_key="test-key")
        result = client.pdf_compress("https://example.com/doc.pdf")

        args, kwargs = mock_request.call_args
        assert kwargs["json"]["file"] == "https://example.com/doc.pdf"
        assert result.file_size == 512

    @patch.object(requests.Session, "request")
    def test_pdf_encrypt(self, mock_request):
        mock_request.return_value = _mock_response(200, {
            "data": {"url": "https://files.example.com/encrypted.pdf", "file_size": 2048},
        })

        client = Client(api_key="test-key")
        result = client.pdf_encrypt("https://example.com/doc.pdf", "secret123")

        args, kwargs = mock_request.call_args
        assert kwargs["json"]["password"] == "secret123"
