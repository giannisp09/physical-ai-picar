from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class FrameResult:
    jpeg_bytes: bytes
    width: int
    height: int


class RobotBackend(ABC):
    """Abstract control surface. Implementations: MockBackend (laptop), PicarBackend (Pi)."""

    @abstractmethod
    def drive(self, direction: str, speed: int, duration_seconds: float) -> None:
        """direction: 'forward' or 'backward'. speed: 0-100. Blocks for duration then stops."""

    @abstractmethod
    def turn(self, angle_degrees: int, duration_seconds: float) -> None:
        """Steer (negative=left, positive=right) and drive forward for duration. Re-centers steering after."""

    @abstractmethod
    def look(self, pan_degrees: int, tilt_degrees: int) -> None:
        """Aim camera. pan: -90..90, tilt: -45..45."""

    @abstractmethod
    def stop(self) -> None:
        """Halt motors immediately."""

    @abstractmethod
    def distance_cm(self) -> float:
        """Ultrasonic forward distance in cm."""

    @abstractmethod
    def capture_frame(self) -> FrameResult:
        """Grab current camera frame as JPEG bytes."""

    @abstractmethod
    def shutdown(self) -> None:
        """Release hardware resources."""


def make_backend(name: str) -> RobotBackend:
    if name == "mock":
        from mock_backend import MockBackend
        return MockBackend()
    if name == "picar":
        from picar_backend import PicarBackend
        return PicarBackend()
    raise ValueError(f"unknown backend: {name!r} (expected 'mock' or 'picar')")
