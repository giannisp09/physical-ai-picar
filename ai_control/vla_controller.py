"""VLA control interface — PLANNED, not yet implemented.

A Vision-Language-Action policy maps camera pixels + the instruction directly
to actions in a single forward pass, instead of an LLM emitting discrete tool
calls. This stub exists to prove the Controller seam is real: dropping in a VLA
means filling in act() below and nothing else — the runner, hardware backend,
observation, and action types are all already in place.

Implementation sketch:
    1. Load a VLA checkpoint (e.g. an OpenVLA / pi0-style policy) in __init__.
    2. In act(): feed obs.frame_rgb (raw HxWx3) + self.goal to the model.
    3. Map the model's output to a neutral Action (Drive/Turn/Look/Stop/Done).
       obs.frame_rgb (raw HxWx3 uint8) is provided by both PicarBackend and the
       MockBackend (when numpy is installed), so the VLA can be developed
       hardware-free against the simulator, exactly like the LLM controller.
"""
from action import Action
from controller import Controller
from observation import Observation


class VLAController(Controller):
    def __init__(self, goal: str):
        self.goal = goal

    def act(self, obs: Observation) -> Action:
        raise NotImplementedError(
            "VLAController is a planned interface — see the Roadmap in README.md. "
            "Implement act() to map obs.frame_rgb + the goal to an Action."
        )
