"""Paradigm-neutral action space: what every AI control interface emits.

A controller's job is to turn an Observation into one of these. An LLM maps its
tool call to one; a VLA maps its output vector to one; a world-model planner
maps its chosen rollout to one. `execute()` is the single place that turns a
neutral Action into concrete RobotBackend calls — no control method talks to
the hardware directly.
"""
from dataclasses import dataclass
from typing import Union

from backend import RobotBackend


@dataclass
class Drive:
    direction: str  # "forward" | "backward"
    speed: int      # 0-100 (backend clamps for safety)
    seconds: float


@dataclass
class Turn:
    angle: int      # -45 (left) .. +45 (right)
    seconds: float


@dataclass
class Look:
    pan: int        # -90 .. 90
    tilt: int       # -45 .. 45


@dataclass
class Stop:
    pass


@dataclass
class Done:
    """Terminal action: goal achieved or judged unreachable. Ends the episode."""
    success: bool
    report: str = ""


# A control method returns exactly one of these per step.
Action = Union[Drive, Turn, Look, Stop, Done]


def execute(backend: RobotBackend, action: Action) -> None:
    """Run a non-terminal action on the hardware. `Done` is handled by the runner."""
    if isinstance(action, Drive):
        backend.drive(action.direction, action.speed, action.seconds)
    elif isinstance(action, Turn):
        backend.turn(action.angle, action.seconds)
    elif isinstance(action, Look):
        backend.look(action.pan, action.tilt)
    elif isinstance(action, Stop):
        backend.stop()
    else:
        raise ValueError(f"execute() cannot run terminal/unknown action: {action!r}")
