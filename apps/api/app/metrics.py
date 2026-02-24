"""Prometheus-compatible metrics collection with histograms and active connections."""

import threading
import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response

# Thread-safe counters
_lock = threading.Lock()
_request_count: dict[str, int] = defaultdict(int)
_error_count: dict[str, int] = defaultdict(int)
_active_connections = 0

# Histogram buckets (seconds)
HISTOGRAM_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, float("inf"))
_histogram_counts: dict[str, list[int]] = defaultdict(lambda: [0] * len(HISTOGRAM_BUCKETS))
_histogram_sum: dict[str, float] = defaultdict(float)
_histogram_total: dict[str, int] = defaultdict(int)


def _normalize_path(path: str) -> str:
    """Collapse UUID/numeric path segments to reduce cardinality."""
    import re

    path = re.sub(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        "{id}",
        path,
    )
    path = re.sub(r"/\d+(?=/|$)", "/{id}", path)
    return path


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path == "/metrics":
            return await call_next(request)

        global _active_connections

        with _lock:
            _active_connections += 1

        start = time.time()
        try:
            response = await call_next(request)
        finally:
            with _lock:
                _active_connections -= 1

        duration = time.time() - start
        method = request.method
        path = _normalize_path(request.url.path)
        status = str(response.status_code)
        key = f"{method}|{path}|{status}"
        hist_key = f"{method}|{path}"

        with _lock:
            _request_count[key] += 1

            # Histogram
            _histogram_sum[hist_key] += duration
            _histogram_total[hist_key] += 1
            for i, bound in enumerate(HISTOGRAM_BUCKETS):
                if duration <= bound:
                    _histogram_counts[hist_key][i] += 1

            if response.status_code >= 400:
                _error_count[f"{method}|{path}|{status}"] += 1

        return response


def metrics_endpoint(request: Request) -> PlainTextResponse:
    """Generate Prometheus text exposition format metrics."""
    lines: list[str] = []

    with _lock:
        # Request count
        lines.append("# HELP http_requests_total Total HTTP requests")
        lines.append("# TYPE http_requests_total counter")
        for key, count in sorted(_request_count.items()):
            method, path, status = key.split("|", 2)
            lines.append(
                f'http_requests_total{{method="{method}",path="{path}",status="{status}"}} {count}'
            )

        # Active connections
        lines.append("")
        lines.append("# HELP http_active_connections Currently active HTTP connections")
        lines.append("# TYPE http_active_connections gauge")
        lines.append(f"http_active_connections {_active_connections}")

        # Latency histogram
        lines.append("")
        lines.append("# HELP http_request_duration_seconds HTTP request duration in seconds")
        lines.append("# TYPE http_request_duration_seconds histogram")
        for hist_key in sorted(_histogram_counts.keys()):
            method, path = hist_key.split("|", 1)
            labels = f'method="{method}",path="{path}"'
            cumulative = 0
            for i, bound in enumerate(HISTOGRAM_BUCKETS):
                cumulative += _histogram_counts[hist_key][i]
                le = "+Inf" if bound == float("inf") else f"{bound}"
                lines.append(
                    f'http_request_duration_seconds_bucket{{{labels},le="{le}"}} {cumulative}'
                )
            lines.append(
                f"http_request_duration_seconds_sum{{{labels}}} {_histogram_sum[hist_key]:.6f}"
            )
            lines.append(
                f"http_request_duration_seconds_count{{{labels}}} {_histogram_total[hist_key]}"
            )

        # Error rates by status code
        lines.append("")
        lines.append("# HELP http_errors_total Total HTTP 4xx/5xx errors by status code")
        lines.append("# TYPE http_errors_total counter")
        for key, count in sorted(_error_count.items()):
            method, path, status = key.split("|", 2)
            lines.append(
                f'http_errors_total{{method="{method}",path="{path}",status="{status}"}} {count}'
            )

    return PlainTextResponse("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")
