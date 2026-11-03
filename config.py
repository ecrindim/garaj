"""Tüm ayarlanabilir değerler. Kodun geri kalanında sabit sayı yok."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from domain.geometry import BoundingBox


@dataclass(frozen=True)
class CameraConfig:
    # AI Camera'nın kendi (IMX500 üzerinde çalışan) COCO nesne tespit modeli
    model_path: str = (
        "/usr/share/imx500-models/imx500_network_ssd_mobilenetv2_fpnlite_320x320_pp.rpk"
    )
    labels_path: Optional[str] = None          # Model etiket içermiyorsa COCO etiket dosyası
    ignore_dash_labels: Optional[bool] = None  # Etiketler kayıksa True/False deneyin
    confidence_threshold: float = 0.55
    show_preview: bool = True                  # Ekran yoksa (SSH) False yapın


@dataclass(frozen=True)
class SafetyConfig:
    # Güvenli bölge, normalize koordinatlar: (x1, y1) sol-üst, (x2, y2) sağ-alt
    safe_zone: BoundingBox = field(default_factory=lambda: BoundingBox(0.20, 0.15, 0.80, 0.90))
    # Sadece bu etiketler dikkate alınır; diğer tüm nesneler yok sayılır.
    vehicle_labels: frozenset[str] = frozenset({"car"})
    living_labels: frozenset[str] = frozenset({"person", "cat", "dog"})


@dataclass(frozen=True)
class GpioConfig:
    red_led_pin: int = 17
    white_led_pin: int = 27
    buzzer_pin: int = 22
    buzzer_on_seconds: float = 0.4
    buzzer_off_seconds: float = 0.4


@dataclass(frozen=True)
class MotorConfig:
    rotation_seconds: float = 6.0  # Simülasyonda 90° dönüşün süreceği süre


@dataclass(frozen=True)
class KeyboardConfig:
    rotate_key: str = "d"
    quit_key: str = "q"


@dataclass(frozen=True)
class AppConfig:
    camera: CameraConfig = field(default_factory=CameraConfig)
    safety: SafetyConfig = field(default_factory=SafetyConfig)
    gpio: GpioConfig = field(default_factory=GpioConfig)
    motor: MotorConfig = field(default_factory=MotorConfig)
    keyboard: KeyboardConfig = field(default_factory=KeyboardConfig)
    log_file: str = "logs/platform.log"
