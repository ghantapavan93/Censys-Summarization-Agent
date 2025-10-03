from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, CONTENT_TYPE_LATEST, generate_latest
import time
from contextlib import contextmanager

# Dedicated registry to avoid default global pollution in some environments
REGISTRY = CollectorRegistry()

# HTTP level
REQ_COUNT = Counter(
    "censai_requests_total",
    "HTTP requests",
    labelnames=("path", "method", "status"),
    registry=REGISTRY,
)
REQ_LATENCY = Histogram(
    "censai_request_latency_seconds",
    "Latency per request",
    labelnames=("path", "method"),
    registry=REGISTRY,
)

# Retrieval and summarization
RETRIEVAL_TOPK = Gauge(
    "censai_retrieval_topk",
    "Top-k used in retrieval",
    registry=REGISTRY,
)
RETRIEVAL_HIT_RATIO = Gauge(
    "censai_retrieval_hit_ratio",
    "Approximate hit ratio (returned/asked)",
    registry=REGISTRY,
)

# Risk rules
RULE_FIRES = Counter(
    "censai_rule_fires_total",
    "Risk rules triggered",
    labelnames=("rule", "severity"),
    registry=REGISTRY,
)

# Stage timings
STAGE_LAT = Histogram(
    "censai_stage_latency_seconds",
    "Latency per pipeline stage",
    labelnames=("stage",),
    buckets=(0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=REGISTRY,
)


@contextmanager
def stage_timer(stage: str):
    t0 = time.perf_counter()
    try:
        yield
    finally:
        dt = time.perf_counter() - t0
        try:
            STAGE_LAT.labels(stage=stage).observe(dt)
        except Exception:
            pass


def metrics_response():
    """Return Prometheus exposition response tuple."""
    return generate_latest(REGISTRY), 200, {"Content-Type": CONTENT_TYPE_LATEST}
