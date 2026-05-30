"""Real hardware backend. Only importable on the Pi (depends on picamera2, board, etc)."""
import io
import os
import sys
import threading
import time

from backend import FrameResult, RobotBackend


def _add_web_to_path():
    here = os.path.dirname(os.path.abspath(__file__))
    web_dir = os.path.join(os.path.dirname(here), "web")
    if web_dir not in sys.path:
        sys.path.insert(0, web_dir)


class PicarBackend(RobotBackend):
    """Drives real motors/servos/camera. Run ONLY on the Pi, with webServer.py stopped."""

    # servo channel assignments (from camera_opencv.py)
    STEER_SERVO = 0
    PAN_SERVO = 1
    TILT_SERVO = 2

    DEFAULT_DRIVE_SPEED = 60  # cap; Claude's requested speed is clamped to this for safety

    def __init__(self):
        _add_web_to_path()
        import move
        import RPIservo
        import ultra
        from picamera2 import Picamera2
        import libcamera

        self._move = move
        self._ultra = ultra

        move.setup()

        self._servos = RPIservo.ServoCtrl()
        self._servos.moveInit()  # centers all servos
        # Start the servo control thread so smooth moves work; we mostly use moveAngle (immediate).
        self._servos.start()

        self._picam2 = Picamera2()
        cfg = self._picam2.preview_configuration
        cfg.size = (320, 240)
        cfg.format = "RGB888"
        cfg.transform = libcamera.Transform(hflip=0, vflip=0)
        cfg.buffer_count = 4
        self._picam2.start()
        time.sleep(0.5)  # camera warm-up

        self._lock = threading.Lock()
        self._stopped = False

    # ------ control ------

    def drive(self, direction: str, speed: int, duration_seconds: float) -> None:
        speed = max(0, min(self.DEFAULT_DRIVE_SPEED, speed))
        duration_seconds = max(0.1, min(3.0, duration_seconds))
        d = 1 if direction == "forward" else -1
        with self._lock:
            self._move.move(speed, d, "no")
        time.sleep(duration_seconds)
        self.stop()

    def turn(self, angle_degrees: int, duration_seconds: float) -> None:
        angle = max(-45, min(45, angle_degrees))
        duration_seconds = max(0.1, min(2.0, duration_seconds))
        with self._lock:
            self._servos.moveAngle(self.STEER_SERVO, angle)
            self._move.move(self.DEFAULT_DRIVE_SPEED, 1, "no")
        time.sleep(duration_seconds)
        with self._lock:
            self._move.motorStop()
            self._servos.moveAngle(self.STEER_SERVO, 0)  # re-center

    def look(self, pan_degrees: int, tilt_degrees: int) -> None:
        pan = max(-90, min(90, pan_degrees))
        tilt = max(-45, min(45, tilt_degrees))
        with self._lock:
            self._servos.moveAngle(self.PAN_SERVO, pan)
            self._servos.moveAngle(self.TILT_SERVO, tilt)

    def stop(self) -> None:
        with self._lock:
            self._move.motorStop()

    def distance_cm(self) -> float:
        try:
            return float(self._ultra.checkdist())
        except Exception:
            return 999.0

    def capture_frame(self) -> FrameResult:
        import cv2
        img = self._picam2.capture_array()
        ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if not ok:
            raise RuntimeError("failed to encode camera frame")
        h, w = img.shape[:2]
        return FrameResult(jpeg_bytes=buf.tobytes(), width=w, height=h, rgb=img)

    def shutdown(self) -> None:
        if self._stopped:
            return
        self._stopped = True
        try:
            self.stop()
        except Exception:
            pass
        try:
            self._picam2.stop()
        except Exception:
            pass
        try:
            self._move.destroy()
        except Exception:
            pass
