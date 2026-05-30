"""Paradigm-neutral observation: what every AI control interface sees.

The same Observation is consumed by an LLM (which uses frame_jpeg), a VLA
(which uses frame_rgb), or a world model (which uses frame_rgb + history).
No control method is privileged in this type.
"""
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Observation:
    distance_cm: float
    frame_jpeg: bytes
    # Raw HxWx3 RGB array, when the backend can provide one (VLAs / world models).
    # Kept optional so the LLM path has zero numpy dependency.
    frame_rgb: Optional[Any] = None
    # Recent prior observations, oldest -> newest, for world models that need
    # temporal context. Empty for memoryless controllers.
    history: tuple = field(default_factory=tuple)
