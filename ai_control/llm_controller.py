"""LLM control interface: Claude drives the robot via vision + tool use.

This is the AI brain built today. It implements Controller.act(): each call
feeds the latest camera frame + distance to Claude, lets it pick exactly one
tool, and maps that tool call onto a neutral Action the runner can execute.
All the Anthropic-specific plumbing (prompt, tool schema, message format) lives
here and nowhere else — swapping in a VLA replaces this file alone.
"""
import base64

from action import Action, Done, Drive, Look, Stop, Turn
from controller import Controller
from observation import Observation


MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You are the brain of a small wheeled robot (Adeept PiCar-B2). \
You see through a forward camera mounted on a pan/tilt head and you drive on four wheels with front-wheel steering.

Your job: given a high-level goal in natural language, achieve it by issuing one tool call per turn. \
After each tool call you will be shown the resulting camera frame and the current forward distance from the ultrasonic sensor. \
Use what you observe to plan the next action.

Conventions:
- Coordinate frame: pan -90° = full left, +90° = full right. Tilt -45° = down, +45° = up. Steering -45° = left, +45° = right.
- Distances are in centimeters. The ultrasonic sensor only sees what's directly in front.
- Drive in short increments (0.3–1.5s) so you can re-observe between moves. Don't issue long drives blindly.
- If forward distance < 25 cm, do not drive forward — turn or back up.
- If you achieve the goal, or determine it's not achievable, call task_complete with a short report.

Think briefly before each tool call (1–2 sentences) about what you see and what you'll do next, then call exactly one tool."""


TOOLS = [
    {
        "name": "drive",
        "description": "Drive straight forward or backward at a given speed for a short duration, then auto-stop.",
        "input_schema": {
            "type": "object",
            "properties": {
                "direction": {"type": "string", "enum": ["forward", "backward"]},
                "speed": {"type": "integer", "minimum": 0, "maximum": 100,
                          "description": "0-100. Will be clamped by the robot for safety."},
                "duration_seconds": {"type": "number", "minimum": 0.1, "maximum": 3.0},
            },
            "required": ["direction", "speed", "duration_seconds"],
        },
    },
    {
        "name": "turn",
        "description": "Steer the front wheels and drive forward briefly to turn. Negative=left, positive=right.",
        "input_schema": {
            "type": "object",
            "properties": {
                "angle_degrees": {"type": "integer", "minimum": -45, "maximum": 45},
                "duration_seconds": {"type": "number", "minimum": 0.1, "maximum": 2.0},
            },
            "required": ["angle_degrees", "duration_seconds"],
        },
    },
    {
        "name": "look",
        "description": "Aim the camera. Use this to look around without moving the body.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pan_degrees": {"type": "integer", "minimum": -90, "maximum": 90},
                "tilt_degrees": {"type": "integer", "minimum": -45, "maximum": 45},
            },
            "required": ["pan_degrees", "tilt_degrees"],
        },
    },
    {
        "name": "stop",
        "description": "Halt all motors immediately. Use if confused or as a safe default.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "task_complete",
        "description": "Declare the goal achieved or unachievable. Ends the session.",
        "input_schema": {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "report": {"type": "string", "description": "One or two sentences for the human operator."},
            },
            "required": ["success", "report"],
        },
    },
]


class LLMController(Controller):
    def __init__(self, goal: str, max_steps: int = 15, dry_run: bool = False):
        self.goal = goal
        self.max_steps = max_steps
        self.dry_run = dry_run
        self.messages: list[dict] = []
        self._pending_tool_use_id: str | None = None
        self._step = 0

        if not dry_run:
            from anthropic import Anthropic
            self._client = Anthropic()
        else:
            self._client = None

    def act(self, obs: Observation) -> Action:
        self._step += 1
        # Append the latest observation to the running conversation. On the first
        # step it seeds the goal; afterward it answers the previous tool call.
        if self._pending_tool_use_id is None:
            self.messages.append(_user_observation(
                intro=f"Goal: {self.goal}\n\nHere is your initial camera view and forward distance.",
                jpeg=obs.frame_jpeg, distance_cm=obs.distance_cm))
        else:
            self.messages.append(_tool_result(
                tool_use_id=self._pending_tool_use_id,
                jpeg=obs.frame_jpeg, distance_cm=obs.distance_cm))

        response = self._call_model()
        assistant_blocks = response["content"]
        self.messages.append({"role": "assistant", "content": assistant_blocks})

        for tb in (b for b in assistant_blocks if b.get("type") == "text"):
            if tb.get("text", "").strip():
                print(f"[claude] {tb['text'].strip()}")

        tool_uses = [b for b in assistant_blocks if b.get("type") == "tool_use"]
        if not tool_uses:
            return Done(success=False, report="Model returned no tool call.")

        tu = tool_uses[0]
        self._pending_tool_use_id = tu["id"]
        return _tool_to_action(tu["name"], tu["input"])

    def _call_model(self) -> dict:
        if self.dry_run:
            return _scripted_response(self._step)

        resp = self._client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
            tools=TOOLS,
            messages=self.messages,
        )
        return {"content": [_block_to_dict(b) for b in resp.content]}


def _tool_to_action(name: str, args: dict) -> Action:
    if name == "drive":
        return Drive(args["direction"], int(args["speed"]), float(args["duration_seconds"]))
    if name == "turn":
        return Turn(int(args["angle_degrees"]), float(args["duration_seconds"]))
    if name == "look":
        return Look(int(args["pan_degrees"]), int(args["tilt_degrees"]))
    if name == "stop":
        return Stop()
    if name == "task_complete":
        return Done(bool(args.get("success", False)), args.get("report", ""))
    return Done(success=False, report=f"Model called unknown tool: {name}")


def _block_to_dict(block) -> dict:
    if block.type == "text":
        return {"type": "text", "text": block.text}
    if block.type == "tool_use":
        return {"type": "tool_use", "id": block.id, "name": block.name, "input": block.input}
    raise RuntimeError(f"unexpected block type: {block.type}")


def _user_observation(*, intro: str, jpeg: bytes, distance_cm: float) -> dict:
    return {
        "role": "user",
        "content": [
            {"type": "text", "text": f"{intro}\nForward distance: {distance_cm:.0f} cm."},
            {"type": "image", "source": {
                "type": "base64", "media_type": "image/jpeg",
                "data": base64.b64encode(jpeg).decode("ascii"),
            }},
        ],
    }


def _tool_result(*, tool_use_id: str, jpeg: bytes, distance_cm: float) -> dict:
    return {
        "role": "user",
        "content": [{
            "type": "tool_result",
            "tool_use_id": tool_use_id,
            "content": [
                {"type": "text", "text": f"Action executed. Forward distance now: {distance_cm:.0f} cm. New camera frame:"},
                {"type": "image", "source": {
                    "type": "base64", "media_type": "image/jpeg",
                    "data": base64.b64encode(jpeg).decode("ascii"),
                }},
            ],
        }],
    }


def _scripted_response(step: int) -> dict:
    """Dry-run fake responses: cycle through tool calls to validate plumbing without an API key."""
    script = [
        ("look", {"pan_degrees": -45, "tilt_degrees": 0}),
        ("look", {"pan_degrees": 45, "tilt_degrees": 0}),
        ("turn", {"angle_degrees": 20, "duration_seconds": 0.5}),
        ("drive", {"direction": "forward", "speed": 30, "duration_seconds": 0.5}),
        ("task_complete", {"success": True, "report": "Dry-run scripted completion."}),
    ]
    name, args = script[min(step - 1, len(script) - 1)]
    return {
        "content": [
            {"type": "text", "text": f"(dry-run) step {step}: calling {name}"},
            {"type": "tool_use", "id": f"dry_{step}", "name": name, "input": args},
        ]
    }
