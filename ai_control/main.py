"""Run an AI control interface against the PiCar.

The backend (robot body) and controller (AI brain) are chosen independently, so
any control method runs on either the laptop simulator or the real robot.

Usage:
    # local smoke test (no hardware, no API key needed):
    python main.py --controller llm --backend mock --dry-run --goal "find the red ball"

    # local test with real Claude calls (needs ANTHROPIC_API_KEY, mock camera/motors):
    python main.py --controller llm --backend mock --goal "find the red ball"

    # on the Pi (after stopping webServer.py: sudo killall python3):
    python main.py --controller llm --backend picar --goal "drive forward until you see a doorway, then stop"
"""
import argparse
import sys

from backend import make_backend
from controller import make_controller
from runner import run_episode


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--controller", choices=["llm", "vla"], default="llm",
                   help="which AI brain drives the robot")
    p.add_argument("--backend", choices=["mock", "picar"], default="mock")
    p.add_argument("--goal", required=True, help="natural-language goal for the robot")
    p.add_argument("--max-steps", type=int, default=15)
    p.add_argument("--dry-run", action="store_true",
                   help="don't call the model; use scripted actions to validate plumbing (llm only)")
    p.add_argument("--no-watchdog", action="store_true", help="disable safety watchdog")
    args = p.parse_args()

    backend = make_backend(args.backend)
    controller = make_controller(args.controller, goal=args.goal,
                                 max_steps=args.max_steps, dry_run=args.dry_run)

    # The safety watchdog only matters when real motors can move.
    watchdog = args.backend == "picar" and not args.no_watchdog

    try:
        result = run_episode(backend, controller,
                             max_steps=args.max_steps, watchdog=watchdog)
        print(f"\n=== result: {result} ===")
        return 0 if result.get("status") == "done" and result.get("success") else 1
    except KeyboardInterrupt:
        print("\ninterrupted")
        return 130
    finally:
        backend.stop()
        backend.shutdown()


if __name__ == "__main__":
    sys.exit(main())
