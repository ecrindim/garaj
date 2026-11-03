"""Tüm ayarlanabilir değerler. Kodun geri kalanında sabit sayı yok."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class CameraConfig:
    # AI Camera'nın kendi (IMX500 üzerinde çalışan) COCO nesne tespit modeli
    model_path: str = (
        "/usr/share/imx500-models/imx500_network_ssd_mobilenetv2_fpnlite_320x320_pp.rpk"
    )
    labels_path: Optional[str] = None          # Model etiket içermiyorsa COCO etiket dosyası
    ignore_dash_labels: Optional[bool] = None  # Etiketler kayıksa True/False deneyin
    confidence_threshold: float = 0.55
    frame_size: tuple[int, int] = (640, 480)  # Ana görüntü (genişlik, yükseklik)
    show_preview: bool = True                  # Ekran yoksa (SSH) False yapın


@dataclass(frozen=True)
class SafetyConfig:
    # Yuvarlak güvenli bölgenin VARSAYILAN değerleri (zone_file yoksa kullanılır).
    # Merkez normalize (0..1) koordinatlarda, yarıçap görüntü yüksekliğine oranlı.
    zone_center_x: float = 0.50
    zone_center_y: float = 0.50
    zone_radius: float = 0.40
    zone_file: str = "zone.json"   # Klavyeden ayarlanıp kaydedilen bölge
    zone_move_step: float = 0.01   # Ok tuşlarıyla her basışta kayma miktarı
    zone_resize_step: float = 0.01 # +/- ile her basışta yarıçap değişimi
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
    save_zone_key: str = "k"   # kaydet
    # Bölge ayar tuşları. Her işlem için birden fazla tuş verilebilir; harfler,
    # Pi'nin klavye düzeni Türkçe klavyeyle uyuşmasa da çalışsın diye var.
    grow_keys: tuple[str, ...] = ("+", "=", "b")    # b = büyüt
    shrink_keys: tuple[str, ...] = ("-", "_", "v")  # v = küçült
    up_keys: tuple[str, ...] = ("UP", "i")
    down_keys: tuple[str, ...] = ("DOWN", "m")
    left_keys: tuple[str, ...] = ("LEFT", "j")
    right_keys: tuple[str, ...] = ("RIGHT", "l")


@dataclass(frozen=True)
class AppConfig:
    camera: CameraConfig = field(default_factory=CameraConfig)
    safety: SafetyConfig = field(default_factory=SafetyConfig)
    gpio: GpioConfig = field(default_factory=GpioConfig)
    motor: MotorConfig = field(default_factory=MotorConfig)
    keyboard: KeyboardConfig = field(default_factory=KeyboardConfig)
    log_file: str = "logs/platform.log"
