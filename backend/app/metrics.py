from prometheus_client import Counter, Histogram, Gauge

# Histogram for tracking E2E request latency
INFERENCE_LATENCY = Histogram(
    "inference_request_latency_seconds",
    "Time spent processing inference requests",
    ["model"]
)

# Counter for tracking tokens
INFERENCE_TOKENS = Counter(
    "inference_tokens_total",
    "Total number of tokens processed",
    ["type", "model"] # type can be 'prompt' or 'completion'
)

# Counter for requests success/failure
INFERENCE_REQUESTS = Counter(
    "inference_requests_total",
    "Total number of inference requests",
    ["status", "model"] # status can be 'success' or 'error'
)

# Gauge for active users/keys (updated periodically or on auth events)
ACTIVE_API_KEYS = Gauge(
    "active_api_keys_total",
    "Number of active API keys with non-zero balance"
)
