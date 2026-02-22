"""Simple Prometheus-compatible metrics collection."""
import time
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response

# Simple counters and histograms (no external dependency needed)
_request_count: dict[str, int] = defaultdict(int)
_request_duration: dict[str, list[float]] = defaultdict(list)
_error_count: dict[str, int] = defaultdict(int)


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path == "/metrics":
            return await call_next(request)

        start = time.time()
        response = await call_next(request)
        duration = time.time() - start

        method = request.method
        path = request.url.path
        status = str(response.status_code)

        key = f'{method}_{path}_{status}'
        _request_count[key] += 1
        _request_duration[key].append(duration)

        if response.status_code >= 500:
            _error_count[f'{method}_{path}'] += 1

        return response


def metrics_endpoint(request: Request) -> PlainTextResponse:
    """Generate Prometheus-format metrics."""
    lines = []
    lines.append("# HELP http_requests_total Total HTTP requests")
    lines.append("# TYPE http_requests_total counter")

    for key, count in sorted(_request_count.items()):
        parts = key.split("_", 2)
        if len(parts) >= 3:
            method, path_status = parts[0], "_".join(parts[1:])
            # Extract status from end
            last_underscore = path_status.rfind("_")
            if last_underscore > 0:
                path = path_status[:last_underscore]
                status = path_status[last_underscore + 1:]
                lines.append(
                    f'http_requests_total{{method="{method}",path="{path}",status="{status}"}} {count}'
                )

    lines.append("")
    lines.append("# HELP http_request_duration_seconds HTTP request duration")
    lines.append("# TYPE http_request_duration_seconds summary")

    for key, durations in sorted(_request_duration.items()):
        if durations:
            avg = sum(durations) / len(durations)
            parts = key.split("_", 2)
            if len(parts) >= 3:
                method = parts[0]
                path_status = "_".join(parts[1:])
                last_underscore = path_status.rfind("_")
                if last_underscore > 0:
                    path = path_status[:last_underscore]
                    lines.append(
                        f'http_request_duration_seconds{{method="{method}",path="{path}",quantile="0.5"}} {avg:.6f}'
                    )

    lines.append("")
    lines.append("# HELP http_errors_total Total HTTP 5xx errors")
    lines.append("# TYPE http_errors_total counter")
    for key, count in sorted(_error_count.items()):
        parts = key.split("_", 1)
        if len(parts) == 2:
            lines.append(f'http_errors_total{{method="{parts[0]}",path="{parts[1]}"}} {count}')

    return PlainTextResponse("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")
