import io
import math
import random
import time

from backend import FrameResult, RobotBackend


class MockBackend(RobotBackend):
    """Prints actions, returns synthetic camera frames. No hardware."""

    def __init__(self):
        self._pan = 0
        self._tilt = 0
        self._step = 0
        # Fake world: a "target" object somewhere in the simulated FOV.
        self._target_world_angle = random.uniform(-60, 60)  # degrees from robot heading
        print(f"[mock] simulated target at heading {self._target_world_angle:+.0f}°")

    def drive(self, direction: str, speed: int, duration_seconds: float) -> None:
        print(f"[mock] drive {direction} speed={speed} for {duration_seconds:.2f}s")
        time.sleep(min(duration_seconds, 0.2))  # don't actually block for seconds during tests
        # simulate target drift relative to robot as it moves
        if direction == "forward":
            self._target_world_angle *= 0.7  # gets "closer" / smaller angular offset
        elif direction == "backward":
            self._target_world_angle *= 1.2

    def turn(self, angle_degrees: int, duration_seconds: float) -> None:
        print(f"[mock] turn angle={angle_degrees:+d}° for {duration_seconds:.2f}s")
        time.sleep(min(duration_seconds, 0.2))
        # turning shifts the world relative to the robot
        self._target_world_angle -= angle_degrees * 0.5

    def look(self, pan_degrees: int, tilt_degrees: int) -> None:
        self._pan = max(-90, min(90, pan_degrees))
        self._tilt = max(-45, min(45, tilt_degrees))
        print(f"[mock] look pan={self._pan:+d}° tilt={self._tilt:+d}°")

    def stop(self) -> None:
        print("[mock] stop")

    def distance_cm(self) -> float:
        # Pretend forward distance shrinks as we close on the target
        d = 30 + abs(self._target_world_angle) * 1.5
        return d

    def capture_frame(self) -> FrameResult:
        self._step += 1
        # Visible target if our pan angle is near the target's world angle
        offset = self._target_world_angle - self._pan
        target_visible = abs(offset) < 30
        jpeg = _render_synthetic_frame(
            step=self._step,
            target_visible=target_visible,
            target_offset_x=offset,
            pan=self._pan,
            tilt=self._tilt,
        )
        return FrameResult(jpeg_bytes=jpeg, width=320, height=240)

    def shutdown(self) -> None:
        print("[mock] shutdown")


def _render_synthetic_frame(*, step, target_visible, target_offset_x, pan, tilt) -> bytes:
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return _solid_jpeg()

    W, H = 320, 240
    img = Image.new("RGB", (W, H), (40, 60, 90))
    draw = ImageDraw.Draw(img)
    # ground line
    draw.line([(0, H * 2 // 3), (W, H * 2 // 3)], fill=(70, 90, 70), width=2)
    # target: a red ball if visible
    if target_visible:
        # map offset (-30..30) → x (0..W); 0 offset → center
        cx = int(W / 2 - target_offset_x * (W / 60))
        cy = H * 2 // 3 - 20
        r = max(10, 40 - int(abs(target_offset_x)))
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(220, 40, 40))
    # HUD overlay
    draw.text((6, 6), f"step={step} pan={pan:+d} tilt={tilt:+d}", fill=(220, 220, 220))
    if not target_visible:
        draw.text((6, H - 20), "(target not in view)", fill=(180, 180, 180))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    return buf.getvalue()


def _solid_jpeg() -> bytes:
    """Minimal valid 1x1 grayscale JPEG (used only if PIL is missing)."""
    import base64
    return base64.b64decode(
        b"/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEB"
        b"AQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEB/8AAEQgAAQABAwEiAAIRAQMRAf/EAB8AAAEFAQEBAQEBAAAAAAAAAAAB"
        b"AgMEBQYHCAkKC//EALUQAAIBAwMCBAMFBQQEAAABfQECAwAEEQUSITFBBhNRYQcicRQygZGhCCNCscEVUtHwJDNi"
        b"coIJChYXGBkaJSYnKCkqNDU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6g4SFhoeIiYqSk5SV"
        b"lpeYmZqio6Slpqeoqaqys7S1tre4ubrCw8TFxsfIycrS09TV1tfY2drh4uPk5ebn6Onq8fLz9PX29/j5+v/aAAwD"
        b"AQACEQMRAD8A/v4ooor/2Q=="
    )
