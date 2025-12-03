"""Quick manual probe to measure tier-0 success rate over N turns.

Runs classify_tier0_fast sequentially and reports success vs fallback/error,
plus basic latency stats. Intended for local/manual use, not CI.
"""

import asyncio
import statistics
from itertools import cycle
from time import perf_counter
from typing import List

from app.services.tier0_classifier import DEFAULT_TIMEOUT_MS, classify_tier0_fast


SAMPLE_INPUTS: List[str] = [
    "hi there",
    "how does staking work?",
    "i feel a bit sad today",
    "i want to hurt myself",
    "tell me about blockchain",
    "good morning",
    "i'm worried about tomorrow",
    "what is a liquidity pool?",
    "hello, can we chat?",
    "i'm so excited for the trip",
]


def _p95(values: List[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = max(0, int(round(0.95 * len(ordered))) - 1)
    return ordered[idx]


async def run_probe(turns: int = 100, timeout_ms: int = DEFAULT_TIMEOUT_MS) -> None:
    successes = 0
    fallbacks = 0
    errors = 0
    latencies: List[float] = []

    for i, text in zip(range(1, turns + 1), cycle(SAMPLE_INPUTS)):
        start = perf_counter()
        try:
            result = await classify_tier0_fast(text, timeout_ms=timeout_ms)
            latencies.append(result.latency_ms)
            if result.fallback_used:
                fallbacks += 1
            else:
                successes += 1
            print(
                f"[{i:03}] {text[:40]:<40} -> intent={result.type:<16} "
                f"emotion={result.emotion:<8} conf={result.confidence:.2f} "
                f"fallback={result.fallback_used} latency={result.latency_ms:.1f}ms"
            )
        except Exception as exc:  # pragma: no cover - manual probe
            errors += 1
            latency_ms = (perf_counter() - start) * 1000.0
            latencies.append(latency_ms)
            print(f"[{i:03}] ERROR for '{text}': {exc} (latency={latency_ms:.1f}ms)")

        await asyncio.sleep(0.05)  # small gap to avoid hammering the API

    total = successes + fallbacks + errors
    success_rate = (successes / total * 100.0) if total else 0.0
    median_latency = statistics.median(latencies) if latencies else 0.0
    p95_latency = _p95(latencies)

    print("\n==== Tier-0 Probe Summary ====")
    print(f"Turns: {total}")
    print(f"Successes (LLM): {successes}")
    print(f"Fallbacks: {fallbacks}")
    print(f"Errors: {errors}")
    print(f"Success rate: {success_rate:.1f}%")
    print(f"Latency median: {median_latency:.1f}ms | p95: {p95_latency:.1f}ms")


if __name__ == "__main__":
    asyncio.run(run_probe())
