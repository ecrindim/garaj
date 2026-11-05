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
    RETURNING_HOME = "HOME'A DÖNÜYOR"
    EMERGENCY_STOPPED = "ACİL DURDURULDU"  # Kilitli; sıfırlanana kadar hareket yok


class PlatformPosition(Enum):
    HOME = "HOME"
    ROTATED = "DÖNMÜŞ"
    BETWEEN = "ARADA"  # Hareket yarıda kesildi



class MotorCommand(Enum):
    NONE = "YOK"
    ROTATE = "DÖNDÜR"
    HOME = "HOME"


@dataclass(frozen=True)
class StatusSnapshot:
    state: PlatformState
    position: PlatformPosition
    command: MotorCommand
    button_pressed: bool
    safety: SafetyReport
    detections: Sequence[Detection]
    fps: float
    seconds_until_home: Optional[float]  # Otomatik home sayacı çalışmıyorsa None


class ObjectDetector(Protocol):
    def read_detections(self) -> list[Detection]: ...


class RotationMotor(Protocol):
    """Platform hep aynı yönde (saat yönünün tersine) 90° döner,
    home'a ters yönde (saat yönünde) geri gelir."""

    @property
    def position(self) -> PlatformPosition: ...
    def rotate_out(self) -> None: ...
    def return_home(self) -> None: ...
    def stop(self) -> None: ...
    def has_reached_target(self) -> bool: ...


class MotorDriver(Protocol):
    """Motora fiziksel komut verir (şimdilik ekrana yazar, ileride röle)."""

    def start_rotate_out(self) -> None: ...  # Saat yönünün tersine
    def start_return_home(self) -> None: ...  # Saat yönünde
    def stop(self) -> None: ...


class RotatedPositionSensor(Protocol):
    """Platform 90° konumundayken (limit switch basılıyken) True döner."""

    def is_triggered(self) -> bool: ...


class PhotoEvent(Enum):
    """Fotoğraf çekilen olaylar; dosya adında kullanılır (ASCII)."""

    ROTATION_APPROVED = "dondurme_onaylandi"
    ROTATION_REJECTED = "dondurme_reddedildi"
    UNSAFE_SITUATION = "guvensiz_durum"
    ROTATION_COMPLETED = "dondurme_tamamlandi"


class PhotoRecorder(Protocol):
    def capture(self, event: PhotoEvent) -> None: ...


class SnapshotCamera(Protocol):
    def save_snapshot(self, path: str) -> None: ...


class CommandButton(Protocol):
    def was_pressed(self) -> bool: ...


class StatusIndicator(Protocol):
    def show_idle(self) -> None: ...
    def show_rotating(self) -> None: ...
    def show_emergency(self) -> None: ...


class StatusDisplay(Protocol):
    def update(self, snapshot: StatusSnapshot) -> None: ...


class ZoneRepository(Protocol):
    def load(self) -> Optional[CircularZone]: ...
    def save(self, zone: CircularZone) -> None: ...
