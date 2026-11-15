# ConvertIntoMP4 Python SDK

Official Python SDK for the [ConvertIntoMP4](https://convertintomp4.com) file conversion API.

- **API docs:** [convertintomp4.com/api-docs](https://convertintomp4.com/api-docs)
- **Examples:** [reach-up/convertintomp4-api-examples](https://github.com/reach-up/convertintomp4-api-examples) (Node.js, Python, Go, .NET)
- **Developers:** [convertintomp4.com/developers](https://convertintomp4.com/developers)

## Installation

```bash
pip install convertintomp4
```

## Requirements

- Python 3.8+
- `requests` library

## Quick Start

```python
from convertintomp4 import Client

client = Client(api_key="your-api-key")

# Quick convert a file
with open("video.mp4", "rb") as f:
    result = client.convert(f, "webm")
    print(f"Job ID: {result['jobId']}")
```

## Configuration

```python
client = Client(
    api_key="your-api-key",
    base_url="https://api.convertintomp4.com/v1",  # default
    sandbox=False,  # True sends X-Sandbox: 1 MB files, 100 POSTs a month per key, counts toward your plan
    timeout=30,     # request timeout in seconds
)
```

## Usage

### Job-Based Conversion

```python
job = client.create_job({
    "tasks": {
        "import-file": {
            "operation": "import/url",
            "url": "https://example.com/video.mp4",
        },
        "convert": {
            "operation": "convert",
            "input": "import-file",
            "output_format": "webm",
            "options": {"quality": "high"},
        },
        "export": {
            "operation": "export/url",
            "input": "convert",
        },
    }
})

# Wait for completion
completed = client.wait_for_job(job.id, interval=2.0, timeout=120.0)
print(f"Status: {completed.status}")
```

### Import from URL

```python
result = client.import_from_url(
    "https://example.com/video.mp4",
    target_format="webm",
    quality="high",
)
```

### Manage Jobs

```python
# List jobs
result = client.list_jobs(status="completed", limit=10)
for job in result["data"]:
    print(f"{job.id}: {job.status}")

# Get job details
job = client.get_job("job_abc123")

# Delete a job
client.delete_job("job_abc123")

# Cancel / retry
client.cancel_job("job_abc123")
client.retry_job("job_abc123")
```

### Download Converted File

```python
data = client.download_file("job_abc123")
with open("output.webm", "wb") as f:
    f.write(data)
```

### Formats

```python
formats = client.list_formats(category="video")
options = client.get_format_options("mp4", "webm")
```

### Webhooks

```python
webhook = client.create_webhook(
    url="https://your-app.com/webhook",
    events=["job.completed", "job.failed"],
    secret="your-secret",
)

webhooks = client.list_webhooks()
client.delete_webhook(webhook.id)
```

### PDF Operations

```python
# OCR
result = client.pdf_ocr("https://example.com/scan.pdf", language="eng")

# Split
parts = client.pdf_split("https://example.com/doc.pdf", ranges=["1-3", "4-6"])

# Merge
merged = client.pdf_merge(["https://example.com/a.pdf", "https://example.com/b.pdf"])

# Encrypt / Decrypt
client.pdf_encrypt("https://example.com/doc.pdf", password="secret")
client.pdf_decrypt("https://example.com/doc.pdf", password="secret")

# Compress
client.pdf_compress("https://example.com/doc.pdf")

# Watermark
client.pdf_watermark("https://example.com/doc.pdf", text="DRAFT", opacity=0.3)

# Extract pages
client.pdf_extract_pages("https://example.com/doc.pdf", pages=[1, 3, 5])

# Rotate
client.pdf_rotate("https://example.com/doc.pdf", angle=90, pages=[2, 4])

# Convert to PDF/A
client.pdf_to_pdfa("https://example.com/doc.pdf")
```

## Error Handling

```python
from convertintomp4 import (
    Client,
    ApiError,
    AuthenticationError,
    RateLimitError,
    TimeoutError,
)

try:
    job = client.get_job("invalid-id")
except AuthenticationError:
    print("Invalid API key")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after}s")
except TimeoutError:
    print("Request timed out")
except ApiError as e:
    print(f"API error {e.status_code}: {e.code} - {e.message}")
```

## Context Manager

The client can be used as a context manager to ensure the HTTP session is properly closed:

```python
with Client(api_key="your-api-key") as client:
    job = client.create_job(...)
```

## License

MIT
