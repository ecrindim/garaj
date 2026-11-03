"""Kontrolcünün bağımlı olduğu soyutlamalar.

Gerçek motor ve kumanda geldiğinde sadece bu arayüzleri uygulayan yeni
sınıflar yazılır; kontrolcü ve iş kuralları değişmez.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Protocol, Sequence

from domain.detection import Detection
from domain.safety import SafetyReport
from domain.zones import CircularZone


class PlatformState(Enum):
    IDLE = "DURUYOR"
    ROTATING = "DÖNÜYOR"


@dataclass(frozen=True)
class StatusSnapshot:
    state: PlatformState
    button_pressed: bool
    rotate_command: int
    safety: SafetyReport
    detections: Sequence[Detection]
    fps: float


class ObjectDetector(Protocol):
    def read_detections(self) -> list[Detection]: ...


class RotationMotor(Protocol):
    def start_rotation(self) -> None: ...
    def stop(self) -> None: ...
    def is_rotation_complete(self) -> bool: ...


class CommandButton(Protocol):
    def was_pressed(self) -> bool: ...


class StatusIndicator(Protocol):
    def show_idle(self) -> None: ...
    def show_rotating(self) -> None: ...


class StatusDisplay(Protocol):
    def update(self, snapshot: StatusSnapshot) -> None: ...


class ZoneRepository(Protocol):
    def load(self) -> Optional[CircularZone]: ...
    def save(self, zone: CircularZone) -> None: ...
