"""Utility helpers for lightweight audio analysis."""

from __future__ import annotations

import audioop
from typing import Dict


def prosody_features(pcm_bytes: bytes) -> Dict[str, str]:
    """Return a coarse intensity classification based on PCM16 RMS."""
    try:
        if not pcm_bytes or len(pcm_bytes) < 2:
            raise ValueError("No samples")

        # audioop operates in C and is far faster than Python loops for RMS
        rms = audioop.rms(pcm_bytes, 2)
        normalized = min(rms / 32768.0, 1.0)

        if normalized < 0.1:
            intensity = "low"
        elif normalized < 0.3:
            intensity = "medium"
        else:
            intensity = "high"

        return {"intensity": intensity}
    except Exception:
        return {"intensity": "low"}
