# Attribution

This repository combines **original work** with **vendor code** from the
robot kit manufacturer. This file makes the boundary explicit.

## Original work — © 2026 Ioannis Pastellas (MIT, see LICENSE)

Written by me. This is the portfolio-relevant content:

| Path          | What it is                                                        |
| ------------- | ----------------------------------------------------------------- |
| `ai_control/` | LLM agent that drives the robot from natural-language goals       |
| `deploy.sh`   | Safe Mac ↔ Raspberry Pi code-sync helper (rsync, never deletes)   |
| `README.md`   | Documentation and architecture notes                              |

## Vendor code — © Adeept

The following directories and files are the **stock software** shipped with
the [Adeept PiCar-B2](https://www.adeept.com/) Raspberry Pi robot car kit.
They were downloaded from Adeept's official distribution and are included
**unmodified (or lightly adapted)** so the project is runnable end-to-end and
so the hardware-driver layer my agent builds on is visible.

| Path                  | What it is                                              |
| --------------------- | ------------------------------------------------------- |
| `web/`                | Adeept's Flask web server, camera, motor/servo drivers  |
| `examples/`           | Adeept's hardware demo scripts (LED, motor, ultrasonic) |
| `setup.py`, `setup_HAT_V3.1.py` | Adeept's kit installers                       |
| `initPosServos.py`    | Adeept's servo-centering utility                        |
| `wifi_hotspot_manager.sh` | Adeept's Wi-Fi hotspot helper                       |

These files remain the property of Adeept and are subject to Adeept's
original license terms. They are reproduced here for interoperability and
demonstration, not claimed as my own work. If you are Adeept and would like
attribution adjusted or content removed, please open an issue.

My `ai_control/picar_backend.py` imports from `web/` (`move`, `RPIservo`,
`ultra`) — that is the seam where my agent meets the vendor's hardware layer.
