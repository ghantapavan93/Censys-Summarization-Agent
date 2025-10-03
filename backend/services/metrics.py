from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import time
from typing import Callable, Any
from functools import wraps

REQUESTS_TOTAL = Counter(
    "censys_requests_total",
    "Total HTTP requests by path and method",
    ["path", "method", "status"],
)
REQUEST_LATENCY = Histogram(
    "censys_request_latency_seconds",
    "HTTP request latency by path",
    ["path"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10),
)

SUMMARIZE_TOTAL = Counter(
    "censys_summarize_total",
    "Total summarize calls",
    ["rewrite_with_ai", "llm"],
)
SUMMARIZE_LATENCY = Histogram(
    "censys_summarize_latency_seconds",
    "Summarize latency",
    ["rewrite_with_ai", "llm"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10),
)

ENRICH_TOTAL = Counter("censys_enrich_total", "Total enrich calls")
EXPORT_TOTAL = Counter("censys_export_total", "Total export calls")

INFLIGHT = Gauge("censys_inflight_requests", "In-flight HTTP requests")


def time_it(hist: Histogram, **labels):
    """Decorator to time functions into a Histogram with label values."""
    def deco(fn: Callable[..., Any]):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return fn(*args, **kwargs)
            finally:
                hist.labels(**labels).observe(time.perf_counter() - start)
        return wrapper
    return deco


def prometheus_asgi_app():
    """Return content-type + body for /metrics route."""
    body = generate_latest()
    return CONTENT_TYPE_LATEST, body
