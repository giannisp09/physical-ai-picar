# Physical AI · PiCar

**Giving an off-the-shelf robot car an LLM brain.** You hand it a goal in plain
English — *"find the red ball"*, *"drive forward until you see a doorway, then
stop"* — and a Claude vision-and-tool-use loop perceives, reasons, and drives
the real hardware one step at a time.

<p align="left">
  <img alt="Python" src="https://img.shields.io/badge/python-3.11%2B-blue">
  <img alt="Model" src="https://img.shields.io/badge/brain-Claude%20(vision%20%2B%20tools)-8A2BE2">
  <img alt="Hardware" src="https://img.shields.io/badge/robot-Adeept%20PiCar--B2-orange">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-green">
</p>

> This is an ongoing **Physical AI** project. The current control method is an
> LLM agent (below). The architecture is built to host *other* control methods
> over time — see the [Roadmap](#roadmap).

---

## The idea

The robot is an [Adeept PiCar-B2](https://www.adeept.com/): four wheels with
front-wheel steering, a pan/tilt camera, and an ultrasonic distance sensor,
running on a Raspberry Pi. Its stock software is a manual web-controlled
joystick app.

This project replaces the human driver with **Claude as a closed-loop agent**:

1. **Perceive** — grab a camera frame + the forward ultrasonic distance.
2. **Reason** — Claude looks at the image and decides the single best next move.
3. **Act** — it calls exactly one tool (`drive`, `turn`, `look`, `stop`).
4. **Repeat** — observe the new frame, re-plan, until the goal is met or judged
   unreachable (`task_complete`).

It is a perception → reasoning → action loop running on physical hardware — the
defining shape of a Physical AI system.

## Architecture

```
                 natural-language goal
                          │
                          ▼
            ┌───────────────────────────┐
            │   Agent loop (agent.py)    │
            │  • sends frame + distance  │
            │  • Claude picks ONE tool   │◀─────────────┐
            │  • executes, re-observes   │              │
            └───────────────────────────┘              │
                          │ tool call                  │ new frame
                          ▼                            │ + distance
            ┌───────────────────────────┐              │
            │  RobotBackend (backend.py) │  abstract control surface
            │  drive / turn / look /     │
            │  stop / distance / frame   │
            └─────────────┬─────────────┘
                 ┌────────┴─────────┐
                 ▼                  ▼
        ┌────────────────┐  ┌──────────────────┐
        │ MockBackend    │  │ PicarBackend     │
        │ laptop, no HW, │  │ real motors,     │
        │ synthetic cam  │  │ servos, camera,  │
        │ (for testing)  │  │ ultrasonic (Pi)  │
        └────────────────┘  └──────────────────┘
```

The **same agent** runs against either backend — so the entire control loop is
developed and tested on a laptop with **zero hardware**, then deployed unchanged
to the Pi. Key design choices:

- **Hardware abstraction** (`RobotBackend`): one interface, two implementations.
- **Mock backend**: a tiny simulated world (a "target" at a random heading,
  shrinking distance, rendered camera frames) so the loop is testable offline.
- **Safety watchdog**: a background thread emergency-stops the motors if anything
  comes within 20 cm — independent of whatever the model decides.
- **Bounded actuation**: speed is clamped (≤60), drive durations are capped, and
  steering/camera angles are constrained, so a bad model output can't do damage.
- **Dry-run mode**: scripted tool calls validate the full plumbing without an API
  key or any network call.

## Quickstart (runs on your laptop — no robot needed)

```bash
cd ai_control
pip install -r requirements.txt

# 1) Plumbing test — no API key, no hardware, scripted moves:
python main.py --backend mock --dry-run --goal "find the red ball"

# 2) Real Claude reasoning against the simulated world (needs an API key):
export ANTHROPIC_API_KEY=sk-ant-...
python main.py --backend mock --goal "find the red ball"
```

You'll see each step print Claude's brief reasoning, the tool it chose, and the
mock world's response.

## Running on the real robot

On the Raspberry Pi (with the camera, motor HAT and ultrasonic sensor wired up):

```bash
# Stop Adeept's stock web server so it isn't fighting for the hardware:
sudo killall python3

cd ai_control
python main.py --backend picar --goal "drive forward until you see a doorway, then stop"
```

The `picar` backend imports Adeept's hardware drivers from [`web/`](web/)
(`move`, `RPIservo`, `ultra`) and adds the camera via `picamera2`. The safety
watchdog is enabled automatically on this backend.

### Deploying code to the Pi

[`deploy.sh`](deploy.sh) syncs this folder between a Mac and the Pi over SSH
(rsync, preview-then-confirm, **never deletes**):

```bash
./deploy.sh diff            # show what differs
./deploy.sh push ai_control # send the agent to the robot
./deploy.sh pull web        # grab robot-side driver tweaks back
```

Configure the target with `PICAR_SSH` / `PICAR_KEY` env vars.

## Repository layout

| Path                                | Author | Description                                  |
| ----------------------------------- | :----: | -------------------------------------------- |
| **`ai_control/`**                   |  Me    | **The LLM agent — the heart of this repo**   |
| &nbsp;&nbsp;`agent.py`              |  Me    | Claude loop: prompt, tools, observe/act      |
| &nbsp;&nbsp;`backend.py`           |  Me    | `RobotBackend` abstract interface            |
| &nbsp;&nbsp;`mock_backend.py`      |  Me    | Laptop simulator + synthetic camera          |
| &nbsp;&nbsp;`picar_backend.py`     |  Me    | Real Raspberry Pi hardware control           |
| &nbsp;&nbsp;`main.py`              |  Me    | CLI entry point + safety watchdog            |
| **`deploy.sh`**                     |  Me    | Mac ↔ Pi sync helper                         |
| `web/`, `examples/`, `setup*.py`    | Adeept | Stock kit software (drivers, demos, install) |

The Adeept-authored files are vendor code included for context and so the
project runs end-to-end. See **[ATTRIBUTION.md](ATTRIBUTION.md)** for the full
breakdown of what's mine vs. the manufacturer's.

## Roadmap

This repo is the LLM-agent chapter of a broader Physical AI exploration. Planned
additions, each as a sibling control method behind the same `RobotBackend`:

- [ ] Classical autonomy baselines (PID line/wall following) for comparison
- [ ] Local vision (on-device object detection) feeding the agent
- [ ] Imitation / reinforcement learning policies
- [ ] Evaluation harness: success rate per goal across methods

## Tech

Python · [Anthropic Claude](https://www.anthropic.com/) (vision + tool use) ·
Raspberry Pi · `picamera2` · OpenCV · Pillow · rsync/SSH

---

*Built on the Adeept PiCar-B2 kit. The AI control layer is my own work — see
[ATTRIBUTION.md](ATTRIBUTION.md).*
