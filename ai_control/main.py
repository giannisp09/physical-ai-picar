"""Language-controlled PiCar via Claude.

Usage:
    # local smoke test (no hardware, no API key needed):
    python main.py --backend mock --dry-run --goal "find the red ball"

    # local test with real Claude calls (needs ANTHROPIC_API_KEY, mock camera/motors):
    python main.py --backend mock --goal "find the red ball"

    # on the Pi (after stopping webServer.py: sudo killall python3):
    python main.py --backend picar --goal "drive forward until you see a doorway, then stop"
"""
import argparse
import sys
import threading
import time

from agent import Agent
from backend import make_backend


def _watchdog(backend, stop_event, threshold_cm=20.0, interval=0.1):
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


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--backend", choices=["mock", "picar"], default="mock")
    p.add_argument("--goal", required=True, help="natural-language goal for the robot")
    p.add_argument("--max-steps", type=int, default=15)
    p.add_argument("--dry-run", action="store_true",
                   help="don't call Anthropic API; use scripted tool calls to validate plumbing")
    p.add_argument("--no-watchdog", action="store_true", help="disable safety watchdog (mock only)")
    args = p.parse_args()

    backend = make_backend(args.backend)

    stop_event = threading.Event()
    wd_thread = None
    if not args.no_watchdog and args.backend == "picar":
        wd_thread = threading.Thread(
            target=_watchdog, args=(backend, stop_event), daemon=True
        )
        wd_thread.start()

    try:
        agent = Agent(backend, goal=args.goal, max_steps=args.max_steps, dry_run=args.dry_run)
        result = agent.run()
        print(f"\n=== result: {result} ===")
        return 0 if result.get("status") == "done" and result.get("success") else 1
    except KeyboardInterrupt:
        print("\ninterrupted")
        return 130
    finally:
        stop_event.set()
        backend.stop()
        backend.shutdown()


if __name__ == "__main__":
    sys.exit(main())
