"""The episode loop — written once, reused by every control method.

This is the paradigm-neutral observe -> decide -> act -> re-observe loop, plus
the safety watchdog. It knows nothing about LLMs, VLAs, or world models; it only
calls Controller.act() and executes whatever neutral Action comes back.
"""
import threading
import time
from collections import deque

from action import Done, execute
from backend import RobotBackend
from controller import Controller
from observation import Observation


def _observe(backend: RobotBackend, history) -> Observation:
    frame = backend.capture_frame()
    dist = backend.distance_cm()
    return Observation(
        distance_cm=dist,
        frame_jpeg=frame.jpeg_bytes,
        frame_rgb=getattr(frame, "rgb", None),
        history=tuple(history),
    )


def _watchdog(backend: RobotBackend, stop_event, threshold_cm=20.0, interval=0.1):
    """Background safety: stop motors if anything gets too close in front."""
    while not stop_event.is_set():
        try:
            d = backend.distance_cm()
            if d < threshold_cm:
                print(f"[watchdog] obstacle at {d:.0f}cm — emergency stop")
                backend.stop()
        except Exception as e:
            print(f"[watchdog] error: {e}")
        time.sleep(interval)


def run_episode(backend: RobotBackend, controller: Controller, *,
                max_steps: int = 15, watchdog: bool = False,
                history_len: int = 4) -> dict:
    """Drive `backend` with `controller` until Done, max_steps, or no action."""
    stop_event = threading.Event()
    if watchdog:
        threading.Thread(
            target=_watchdog, args=(backend, stop_event), daemon=True
        ).start()

    history: deque = deque(maxlen=history_len)
    try:
        obs = _observe(backend, history)
        for step in range(1, max_steps + 1):
            print(f"\n--- step {step}/{max_steps} (forward distance: {obs.distance_cm:.0f} cm) ---")
            action = controller.act(obs)
            print(f"[action] {action}")

            if isinstance(action, Done):
                return {"status": "done", "success": action.success,
                        "report": action.report, "steps": step}

            execute(backend, action)
            history.append(obs)
            obs = _observe(backend, history)

        return {"status": "max_steps", "steps": max_steps}
    finally:
        stop_event.set()
