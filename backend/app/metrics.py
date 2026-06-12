"""Prometheus metrics — METADATA ONLY. No prompt/response bodies, no intake text,
no transcript content ever touches a label or value (safety §8)."""

from prometheus_client import Counter, Histogram

sessions_created = Counter(
    "dc_sessions_created_total", "Sessions created", ["crisis"]
)
turns_generated = Counter(
    "dc_turns_generated_total", "Agent turns generated", ["role"]
)
verdicts_total = Counter("dc_verdicts_total", "Verdicts delivered")
crisis_triggered = Counter(
    "dc_crisis_triggered_total", "Crisis path triggered", ["stage"]
)
rate_limited = Counter("dc_rate_limited_total", "Session creates rejected by rate limit")
shares_created = Counter("dc_shares_created_total", "Share links minted", ["scope", "gallery"])

groq_tokens = Counter(
    "dc_groq_tokens_total", "Groq tokens consumed", ["direction", "model"]
)
turn_latency = Histogram(
    "dc_turn_latency_seconds",
    "Wall time per generated agent turn",
    ["role"],
    buckets=(0.5, 1, 2, 4, 8, 16, 32),
)

http_requests = Counter(
    "dc_http_requests_total", "HTTP requests", ["method", "path", "status"]
)
http_latency = Histogram(
    "dc_http_request_seconds", "HTTP request latency", ["method", "path"]
)
