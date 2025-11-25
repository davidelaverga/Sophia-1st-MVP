"""
Prometheus metrics for Sophia voice backend.

Tracks intent classification, mode routing, and utility path selection
for M3 milestone routing system.
"""

from prometheus_client import Counter

# Intent classification metrics
intent_total = Counter(
    "intent_total",
    "Total number of intent classifications",
    ["intent"],  # Values: EMOTIONAL_SUPPORT, UTILITY
)

# Mode routing metrics
mode_total = Counter(
    "mode_total",
    "Total number of mode routings",
    [
        "mode"
    ],  # Values: EMOTIONAL_SUPPORT, UTILITY_DIRECT, UTILITY_LIGHT, UTILITY_AGENTIC
)

# Utility path selection metrics
utility_path_total = Counter(
    "utility_path_total",
    "Total number of utility path selections",
    ["path"],  # Values: DIRECT, LIGHT, AGENTIC
)


# ========================================================================
# DEPRECATED DeFi METRICS - DO NOT USE IN M3
# ========================================================================
# The following metrics are for legacy DeFi functionality and should NOT
# be logged or incremented. Customer requirement: stop tracking DeFi metrics.
# Code remains for reference only.
# ========================================================================

# defi_intent_counter = Counter(
#     "defi_intent_counter",
#     "DeFi-specific intent classifications (DEPRECATED - DO NOT USE)",
#     ["intent_type"],
# )

# defi_rag_latency = Histogram(
#     "defi_rag_latency",
#     "DeFi RAG query latency in seconds (DEPRECATED - DO NOT USE)",
#     buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
# )

# defi_faq_category_requests = Counter(
#     "defi_faq_category_requests",
#     "DeFi FAQ category request counts (DEPRECATED - DO NOT USE)",
#     ["category"],
# )


def track_intent(intent: str) -> None:
    """
    Track intent classification.

    Args:
        intent: Intent value (EMOTIONAL_SUPPORT or UTILITY)
    """
    intent_total.labels(intent=intent).inc()


def track_mode(mode: str) -> None:
    """
    Track mode routing.

    Args:
        mode: Mode value (EMOTIONAL_SUPPORT, UTILITY_DIRECT, UTILITY_LIGHT, UTILITY_AGENTIC)
    """
    mode_total.labels(mode=mode).inc()


def track_utility_path(path: str) -> None:
    """
    Track utility path selection.

    Args:
        path: Path value (DIRECT, LIGHT, AGENTIC)
    """
    utility_path_total.labels(path=path).inc()
