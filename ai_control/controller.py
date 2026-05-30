"""The control-method seam.

A Controller is an AI "brain": it maps one Observation to one Action. Swapping
the robot's intelligence — LLM agent, VLA policy, world-model planner — means
implementing this one method. Controllers never touch hardware (that's the
RobotBackend, via action.execute) and never own the episode loop (that's the
runner). They hold only their own policy state.
"""
from abc import ABC, abstractmethod

from action import Action
from observation import Observation


class Controller(ABC):
    @abstractmethod
    def act(self, obs: Observation) -> Action:
        """Decide the single next action from the current observation.

        Called once per step by the runner. Controllers may keep internal state
        across calls (e.g. an LLM's running conversation, a world model's belief
        state). Return a `Done` action to end the episode.
        """


def make_controller(name: str, *, goal: str, max_steps: int = 15,
                    dry_run: bool = False) -> Controller:
    """Factory mirroring make_backend: pick the AI brain by name."""
    if name == "llm":
        from llm_controller import LLMController
        return LLMController(goal=goal, max_steps=max_steps, dry_run=dry_run)
    if name == "vla":
        from vla_controller import VLAController
        return VLAController(goal=goal)
    raise ValueError(f"unknown controller: {name!r} (expected 'llm' or 'vla')")
