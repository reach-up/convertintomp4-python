"""ConvertIntoMP4 API client."""

import time
from typing import Any, BinaryIO, Dict, List, Optional, Union
from urllib.parse import urlencode

import requests

from .exceptions import (
    ApiError,
    AuthenticationError,
    ConvertIntoMP4Error,
    NotFoundError,
    RateLimitError,
    TimeoutError,
    ValidationError,
)
from .types import (
    Format,
    FormatOption,
    Job,
    PdfOperationResult,
    PdfPermissions,
    WaitOptions,
    Webhook,
)

DEFAULT_BASE_URL = "https://api.convertintomp4.com/v1"


class Client:
    """ConvertIntoMP4 API client.

    Args:
        api_key: Your API key.
        base_url: Base URL for the API. Defaults to production.
        sandbox: If True, send the X-Sandbox header (stricter sandbox limits).
        timeout: Request timeout in seconds. Defaults to 30.
        headers: Additional headers to include in requests.

    Example::

        from convertintomp4 import Client

        client = Client(api_key="your-api-key")
        job = client.create_job({
            "tasks": {
                "import": {"operation": "import/url", "url": "https://example.com/video.mp4"},
                "convert": {"operation": "convert", "input": "import", "output_format": "webm"},
                "export": {"operation": "export/url", "input": "convert"},
            }
        })
    """

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        sandbox: bool = False,
        timeout: int = 30,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        if not api_key:
            raise ConvertIntoMP4Error("API key is required")

        self.api_key = api_key
        # Sandbox is a request header on the normal API host (there is no separate host).
        self.base_url = base_url or DEFAULT_BASE_URL
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "convertintomp4-python/1.0.0",
            }
        )
        if sandbox:
            self._session.headers["X-Sandbox"] = "true"
        if headers:
            self._session.headers.update(headers)

    def close(self) -> None:
        """Close the HTTP session."""
        self._session.close()

    def __enter__(self) -> "Client":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    # =========================================================================
    # HTTP Methods
    # =========================================================================

    def _request(
        self,
        method: str,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Make an HTTP request to the API."""
        url = f"{self.base_url}{path}"

        try:
            response = self._session.request(
                method=method,
                url=url,
                json=json,
                params=params,
                timeout=self.timeout,
            )
        except requests.exceptions.Timeout:
            raise TimeoutError(f"Request to {path} timed out after {self.timeout}s")
        except requests.exceptions.ConnectionError as e:
            raise ConvertIntoMP4Error(f"Connection error: {e}")
        except requests.exceptions.RequestException as e:
            raise ConvertIntoMP4Error(f"Request failed: {e}")

        return self._handle_response(response)

    def _handle_response(self, response: requests.Response) -> Any:
        """Handle the API response and raise appropriate exceptions."""
        if response.status_code == 204:
            return None

        try:
            data = response.json()
        except ValueError:
            if response.ok:
                return response.content
            raise ApiError(
                response.status_code,
                "PARSE_ERROR",
                "Failed to parse response as JSON",
            )

        if not response.ok:
            error = data.get("error", {}) if isinstance(data, dict) else {}
            if isinstance(error, str):
                # Older flat shape: {"error": "message", "code": "..."}
                error = {"message": error, "code": data.get("code")}
            code = error.get("code") or "UNKNOWN_ERROR"
            message = error.get("message", "An unknown error occurred")
            details = error.get("details")

            if response.status_code == 401:
                raise AuthenticationError(message)
            if response.status_code == 404:
                raise NotFoundError(message=message, code=code)
            if response.status_code == 429 and code != "QUOTA_EXCEEDED":
                retry_after = response.headers.get("Retry-After")
                raise RateLimitError(
                    retry_after=int(retry_after) if retry_after else None
                )
            if response.status_code == 400:
                raise ValidationError(message, details)

            raise ApiError(response.status_code, code, message, details)

        return data.get("data", data)

    def _upload(
        self,
        path: str,
        file: Union[BinaryIO, bytes],
        fields: Dict[str, str],
        filename: Optional[str] = None,
    ) -> Any:
        """Upload a file via multipart form data."""
        url = f"{self.base_url}{path}"

        if isinstance(file, bytes):
            files = {"file": (filename or "upload", file)}
        else:
            files = {"file": (filename or getattr(file, "name", "upload"), file)}

        try:
            # Remove Content-Type header for multipart upload (requests sets it)
            headers = dict(self._session.headers)
            headers.pop("Content-Type", None)

            response = requests.post(
                url,
                files=files,
                data=fields,
                headers=headers,
                timeout=self.timeout,
            )
        except requests.exceptions.Timeout:
            raise TimeoutError(f"Upload to {path} timed out after {self.timeout}s")
        except requests.exceptions.RequestException as e:
            raise ConvertIntoMP4Error(f"Upload failed: {e}")

        return self._handle_response(response)

    # =========================================================================
    # Job Methods
    # =========================================================================

    def create_job(self, request: Dict[str, Any]) -> Job:
        """Create a new conversion job with one or more tasks.

        Args:
            request: Job configuration with tasks, optional tag and webhook_url.

        Returns:
            The created Job.

        Example::

            job = client.create_job({
                "tasks": {
                    "import": {"operation": "import/url", "url": "https://example.com/video.mp4"},
                    "convert": {"operation": "convert", "input": "import", "output_format": "webm"},
                    "export": {"operation": "export/url", "input": "convert"},
                }
            })
        """
        data = self._request("POST", "/jobs", json=request)
        return Job.from_dict(data)

    def get_job(self, job_id: str) -> Job:
        """Get the details and status of a specific job.

        Args:
            job_id: The job identifier.

        Returns:
            The Job with current status.
        """
        data = self._request("GET", f"/jobs/{job_id}")
        return Job.from_dict(data)

    def list_jobs(
        self,
        status: Optional[str] = None,
        tag: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """List all jobs, optionally filtered.

        Args:
            status: Filter by job status.
            tag: Filter by tag.
            limit: Maximum number of results. Defaults to 20.
            offset: Offset for pagination. Defaults to 0.

        Returns:
            Dict with 'data' (list of Jobs) and 'meta' (pagination info).
        """
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status
        if tag:
            params["tag"] = tag

        result = self._request("GET", "/jobs", params=params)

        if isinstance(result, dict):
            jobs = [Job.from_dict(j) for j in result.get("data", result) if isinstance(j, dict)]
            return {"data": jobs, "meta": result.get("meta", {})}

        if isinstance(result, list):
            return {"data": [Job.from_dict(j) for j in result], "meta": {}}

        return {"data": [], "meta": {}}

    def delete_job(self, job_id: str) -> None:
        """Delete a job and its associated files.

        Args:
            job_id: The job identifier.
        """
        self._request("DELETE", f"/jobs/{job_id}")

    def get_job_webhook_secret(self) -> Dict[str, Any]:
        """The secret that signs webhooks sent to a job's ``webhook_url``.

        Verify deliveries with :func:`convertintomp4.verify_job_webhook`.
        """
        return self._request("GET", "/jobs/webhook-secret")

    def rotate_job_webhook_secret(self) -> Dict[str, Any]:
        """Issue a new job webhook secret; deliveries signed after this use it."""
        return self._request("POST", "/jobs/webhook-secret/rotate")

    def cancel_job(self, job_id: str) -> Job:
        """Cancel a running job.

        Args:
            job_id: The job identifier.

        Returns:
            The cancelled Job.
        """
        data = self._request("POST", f"/jobs/{job_id}/cancel")
        return Job.from_dict(data)

    def retry_job(self, job_id: str) -> Job:
        """Retry a failed job.

        Args:
            job_id: The job identifier.

        Returns:
            The retried Job.
        """
        data = self._request("POST", f"/jobs/{job_id}/retry")
        return Job.from_dict(data)

    def wait_for_job(
        self,
        job_id: str,
        interval: float = 1.0,
        timeout: float = 300.0,
    ) -> Job:
        """Poll a job until it reaches a terminal state.

        Args:
            job_id: The job identifier.
            interval: Polling interval in seconds. Defaults to 1.0.
            timeout: Maximum wait time in seconds. Defaults to 300 (5 minutes).

        Returns:
            The completed/failed/cancelled Job.

        Raises:
            TimeoutError: If the job does not complete within the timeout.
        """
        start_time = time.monotonic()

        while time.monotonic() - start_time < timeout:
            job = self.get_job(job_id)

            if job.status in ("completed", "failed", "cancelled"):
                return job

            time.sleep(interval)

        raise TimeoutError(
            f"Job {job_id} did not complete within {timeout} seconds"
        )

    # =========================================================================
    # Quick Convert Methods
    # =========================================================================

    def convert(
        self,
        file: Union[BinaryIO, bytes],
        target_format: str,
        filename: Optional[str] = None,
        **options: Any,
    ) -> Dict[str, Any]:
        """Quick file conversion - upload and convert in one step.

        Args:
            file: File object or bytes to convert.
            target_format: Target format (e.g., 'webm', 'mp3', 'png').
            filename: Optional filename for the upload.
            **options: Additional conversion options (quality, resolution, etc.).

        Returns:
            Dict with jobId, status, and statusUrl.
        """
        fields = {"targetFormat": target_format}
        for key, value in options.items():
            fields[key] = str(value)

        return self._upload("/convert", file, fields, filename)

    def upload_file(
        self,
        file: Union[BinaryIO, bytes],
        target_format: str,
        filename: Optional[str] = None,
        **options: Any,
    ) -> Dict[str, Any]:
        """Upload a file for conversion.

        Alias for `convert()`.
        """
        return self.convert(file, target_format, filename, **options)

    def import_from_url(
        self,
        url: str,
        target_format: str,
        filename: Optional[str] = None,
        **options: Any,
    ) -> Dict[str, Any]:
        """Import a file from a URL and start conversion.

        Args:
            url: URL of the file to import.
            target_format: Target format for conversion.
            filename: Optional filename override.
            **options: Additional conversion options.

        Returns:
            Dict with jobId, status, and statusUrl.
        """
        body: Dict[str, Any] = {"url": url, "targetFormat": target_format}
        if filename:
            body["filename"] = filename
        body.update(options)
        return self._request("POST", "/import/url", json=body)

    def download_file(self, job_id: str) -> bytes:
        """Download a converted file by job ID.

        Args:
            job_id: The job identifier.

        Returns:
            The file contents as bytes.
        """
        url = f"{self.base_url}/download/{job_id}"
        response = self._session.get(url, timeout=self.timeout)

        if not response.ok:
            self._handle_response(response)

        return response.content

    # =========================================================================
    # Format Methods
    # =========================================================================

    def list_formats(self, category: Optional[str] = None) -> List[Format]:
        """List all supported formats.

        Args:
            category: Optionally filter by category (video, audio, image, document).

        Returns:
            List of Format objects.
        """
        params = {}
        if category:
            params["category"] = category

        data = self._request("GET", "/formats", params=params or None)

        if isinstance(data, list):
            return [Format.from_dict(f) for f in data]
        return []

    def get_format(self, format_id: str) -> Format:
        """Get detailed info about a specific format.

        Args:
            format_id: The format identifier (e.g., 'mp4', 'webm').

        Returns:
            Format object.
        """
        data = self._request("GET", f"/formats/{format_id}")
        return Format.from_dict(data)

    def get_format_options(
        self, input_format: str, output_format: str
    ) -> Dict[str, Any]:
        """Get available conversion options for a format pair.

        Args:
            input_format: Source format.
            output_format: Target format.

        Returns:
            Dict with input_format, output_format, and list of options.
        """
        params = {
            "input_format": input_format,
            "output_format": output_format,
        }
        return self._request("GET", "/formats/options", params=params)

    # =========================================================================
    # Webhook Methods
    # =========================================================================

    def create_webhook(
        self,
        url: str,
        events: List[str],
        secret: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Webhook:
        """Create a new webhook subscription.

        Args:
            url: The URL to receive webhook events.
            events: List of event types to subscribe to.
            secret: Optional secret for signing webhook payloads.
            metadata: Optional metadata key-value pairs.

        Returns:
            The created Webhook.
        """
        body: Dict[str, Any] = {"url": url, "events": events}
        if secret:
            body["secret"] = secret
        if metadata:
            body["metadata"] = metadata

        data = self._request("POST", "/webhooks", json=body)
        return Webhook.from_dict(data)

    def list_webhooks(self) -> List[Webhook]:
        """List all registered webhooks.

        Returns:
            List of Webhook objects.
        """
        data = self._request("GET", "/webhooks")
        if isinstance(data, list):
            return [Webhook.from_dict(w) for w in data]
        return []

    def get_webhook(self, webhook_id: str) -> Webhook:
        """Get a specific webhook by ID.

        Args:
            webhook_id: The webhook identifier.

        Returns:
            Webhook object.
        """
        data = self._request("GET", f"/webhooks/{webhook_id}")
        return Webhook.from_dict(data)

    def delete_webhook(self, webhook_id: str) -> None:
        """Delete a webhook subscription.

        Args:
            webhook_id: The webhook identifier.
        """
        self._request("DELETE", f"/webhooks/{webhook_id}")

    # =========================================================================
    # PDF Operations
    # =========================================================================

    def pdf_ocr(
        self, file: str, language: Optional[str] = None
    ) -> PdfOperationResult:
        """Perform OCR on a PDF file.

        Args:
            file: URL of the PDF file.
            language: OCR language (e.g., 'eng', 'deu').

        Returns:
            PdfOperationResult with output URL and metadata.
        """
        body: Dict[str, Any] = {"file": file}
        if language:
            body["language"] = language
        data = self._request("POST", "/pdf/ocr", json=body)
        return PdfOperationResult.from_dict(data)

    def pdf_split(self, file: str, ranges: List[str]) -> List[PdfOperationResult]:
        """Split a PDF into multiple documents.

        Args:
            file: URL of the PDF file.
            ranges: List of page ranges (e.g., ['1-3', '4-6']).

        Returns:
            List of PdfOperationResult, one per range.
        """
        body = {"file": file, "ranges": ranges}
        data = self._request("POST", "/pdf/split", json=body)
        if isinstance(data, list):
            return [PdfOperationResult.from_dict(d) for d in data]
        return [PdfOperationResult.from_dict(data)]

    def pdf_merge(self, files: List[str]) -> PdfOperationResult:
        """Merge multiple PDF files into one.

        Args:
            files: List of URLs of PDF files to merge.

        Returns:
            PdfOperationResult with the merged PDF URL.
        """
        body = {"files": files}
        data = self._request("POST", "/pdf/merge", json=body)
        return PdfOperationResult.from_dict(data)

    def pdf_encrypt(
        self,
        file: str,
        password: str,
        permissions: Optional[PdfPermissions] = None,
    ) -> PdfOperationResult:
        """Encrypt a PDF with a password.

        Args:
            file: URL of the PDF file.
            password: Password to set.
            permissions: Optional permission restrictions.

        Returns:
            PdfOperationResult with the encrypted PDF URL.
        """
        body: Dict[str, Any] = {"file": file, "password": password}
        if permissions:
            body["permissions"] = dict(permissions)
        data = self._request("POST", "/pdf/encrypt", json=body)
        return PdfOperationResult.from_dict(data)

    def pdf_decrypt(self, file: str, password: str) -> PdfOperationResult:
        """Decrypt a password-protected PDF.

        Args:
            file: URL of the PDF file.
            password: Password to unlock the PDF.

        Returns:
            PdfOperationResult with the decrypted PDF URL.
        """
        body = {"file": file, "password": password}
        data = self._request("POST", "/pdf/decrypt", json=body)
        return PdfOperationResult.from_dict(data)

    def pdf_rotate(
        self,
        file: str,
        angle: int,
        pages: Optional[List[int]] = None,
    ) -> PdfOperationResult:
        """Rotate pages in a PDF.

        Args:
            file: URL of the PDF file.
            angle: Rotation angle in degrees (90, 180, 270).
            pages: Optional list of page numbers to rotate. Rotates all if omitted.

        Returns:
            PdfOperationResult with the rotated PDF URL.
        """
        body: Dict[str, Any] = {"file": file, "angle": angle}
        if pages:
            body["pages"] = pages
        data = self._request("POST", "/pdf/rotate", json=body)
        return PdfOperationResult.from_dict(data)

    def pdf_compress(self, file: str) -> PdfOperationResult:
        """Compress a PDF to reduce file size.

        Args:
            file: URL of the PDF file.

        Returns:
            PdfOperationResult with the compressed PDF URL.
        """
        body = {"file": file}
        data = self._request("POST", "/pdf/compress", json=body)
        return PdfOperationResult.from_dict(data)

    def pdf_to_pdfa(self, file: str) -> PdfOperationResult:
        """Convert a PDF to PDF/A archival format.

        Args:
            file: URL of the PDF file.

        Returns:
            PdfOperationResult with the PDF/A URL.
        """
        body = {"file": file}
        data = self._request("POST", "/pdf/to-pdfa", json=body)
        return PdfOperationResult.from_dict(data)

    def pdf_extract_pages(
        self, file: str, pages: List[int]
    ) -> PdfOperationResult:
        """Extract specific pages from a PDF.

        Args:
            file: URL of the PDF file.
            pages: List of page numbers to extract.

        Returns:
            PdfOperationResult with the extracted pages PDF URL.
        """
        body = {"file": file, "pages": pages}
        data = self._request("POST", "/pdf/extract-pages", json=body)
        return PdfOperationResult.from_dict(data)

    def pdf_watermark(
        self,
        file: str,
        text: Optional[str] = None,
        image: Optional[str] = None,
        opacity: Optional[float] = None,
    ) -> PdfOperationResult:
        """Add a watermark to a PDF.

        Args:
            file: URL of the PDF file.
            text: Watermark text. Either text or image must be provided.
            image: URL of watermark image. Either text or image must be provided.
            opacity: Watermark opacity (0.0 to 1.0).

        Returns:
            PdfOperationResult with the watermarked PDF URL.
        """
        body: Dict[str, Any] = {"file": file}
        if text:
            body["text"] = text
        if image:
            body["image"] = image
        if opacity is not None:
            body["opacity"] = opacity
        data = self._request("POST", "/pdf/watermark", json=body)
        return PdfOperationResult.from_dict(data)

    # =========================================================================
    # Presigned Upload Methods (direct to storage)
    # =========================================================================

    def get_presigned_upload_url(
        self,
        filename: str,
        content_type: str = "application/octet-stream",
        file_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get a presigned URL for uploading a file directly to storage.

        This bypasses the API server for large file uploads.

        Args:
            filename: Name of the file being uploaded.
            content_type: MIME type of the file.
            file_size: Optional file size hint for quota checking.

        Returns:
            Dict with uploadUrl, storageKey, expiresIn, etc.

        Example::

            presign = client.get_presigned_upload_url("video.mp4", "video/mp4")
            # Upload directly to storage
            requests.put(presign["uploadUrl"], data=file_data)
            # Start conversion
            result = client.convert_from_storage(presign["storageKey"], "mp4", "webm")
        """
        body: Dict[str, Any] = {
            "filename": filename,
            "contentType": content_type,
        }
        if file_size is not None:
            body["fileSize"] = file_size
        return self._request("POST", "/uploads/presign", json=body)

    def convert_from_storage(
        self,
        storage_key: str,
        source_format: str,
        target_format: str,
        original_name: Optional[str] = None,
        tool_operation: Optional[str] = None,
        **options: Any,
    ) -> Dict[str, Any]:
        """Start a conversion from a file already uploaded to storage.

        Args:
            storage_key: The storage key from get_presigned_upload_url().
            source_format: Source file format (e.g., "mp4").
            target_format: Target conversion format (e.g., "webm").
            original_name: Optional original filename.
            tool_operation: Optional tool operation.
            **options: Additional conversion options.

        Returns:
            Dict with jobId, status, statusUrl, realtimeUrl, sseUrl, etc.
        """
        body: Dict[str, Any] = {
            "storageKey": storage_key,
            "sourceFormat": source_format,
            "targetFormat": target_format,
        }
        if original_name:
            body["originalName"] = original_name
        if tool_operation:
            body["toolOperation"] = tool_operation
        body.update(options)
        return self._request("POST", "/convert/storage", json=body)

    def upload_direct(
        self,
        file_data: Union[bytes, BinaryIO],
        filename: str,
        content_type: str,
        target_format: str,
        **options: Any,
    ) -> Dict[str, Any]:
        """Upload a file directly to storage and start conversion in one step.

        Combines get_presigned_upload_url + PUT upload + convert_from_storage.

        Args:
            file_data: File content as bytes or file-like object.
            filename: Name of the file.
            content_type: MIME type.
            target_format: Target conversion format.
            **options: Additional conversion options.

        Returns:
            Dict with jobId, status, and real-time streaming URLs.
        """
        # Get presigned URL
        presign = self.get_presigned_upload_url(filename, content_type)

        # Upload directly to storage
        if hasattr(file_data, "read"):
            data = file_data.read()
        else:
            data = file_data

        resp = requests.put(
            presign["uploadUrl"],
            data=data,
            headers={"Content-Type": content_type},
            timeout=self.timeout,
        )
        resp.raise_for_status()

        # Derive source format
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        return self.convert_from_storage(
            storage_key=presign["storageKey"],
            source_format=ext,
            target_format=target_format,
            original_name=filename,
            **options,
        )

    # =========================================================================
    # Real-time Job Streaming (SSE)
    # =========================================================================

    def stream_job_updates(
        self, job_id: str
    ):
        """Stream real-time job updates via Server-Sent Events (SSE).

        Yields JobUpdate dicts as they arrive. Automatically closes on
        terminal events (completed, failed).

        Args:
            job_id: The job ID to stream updates for.

        Yields:
            Dict with type, jobId, timestamp, progress, error, outputUrl, etc.

        Example::

            for update in client.stream_job_updates(job_id):
                print(f"{update['type']}: {update.get('progress', 0)}%")
                if update["type"] in ("completed", "failed"):
                    break
        """
        import json

        base_origin = self.base_url.replace("/v1", "")
        url = f"{base_origin}/sse/jobs/{job_id}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "text/event-stream",
            "User-Agent": "convertintomp4-python/1.0.0",
        }

        with requests.get(url, headers=headers, stream=True, timeout=None) as resp:
            resp.raise_for_status()

            event_type = ""
            event_data = ""

            for line in resp.iter_lines(decode_unicode=True):
                if line is None:
                    continue

                if line.startswith("event: "):
                    event_type = line[7:].strip()
                elif line.startswith("data: "):
                    event_data = line[6:].strip()
                elif line == "" and event_data:
                    if event_type != "connected":
                        try:
                            update = json.loads(event_data)
                            yield update
                            if update.get("type") in ("completed", "failed"):
                                return
                        except json.JSONDecodeError:
                            pass
                    event_type = ""
                    event_data = ""
