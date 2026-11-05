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
    emergency_blink_seconds: float = 0.15  # Acil durumda kırmızı LED hızlı yanıp söner


@dataclass(frozen=True)
class MotorConfig:
    # --- Konum: iki mekanik limit switch (NO kontak, bir ucu GPIO, diğer ucu GND) ---
    # False: switch'ler takılmadan simülasyon, hedefe `rotation_seconds` sonra varılır.
    use_limit_switches: bool = False
    home_switch_pin: int = 4          # GPIO4  (fiziksel pin 7)
    rotated_switch_pin: int = 24      # GPIO24 (fiziksel pin 18)
    # Motor çalıştıktan bu süre sonra platform hâlâ başlangıç switch'indeyse acil durdurulur
    departure_timeout_seconds: float = 3.0
    rotation_seconds: float = 6.0     # Simülasyonda home ↔ 90° hareketinin süresi

    # --- Motor komutu: 4 kanallı röle modülü (SRD-05VDC-SL-C), JD-VCC jumper'ı çıkarılmış ---
    # False: röleler yerine komutlar ekrana yazılır.
    use_relays: bool = False
    rotate_relay_pin: int = 2         # GPIO2 (fiziksel pin 3) → IN1: saat yönünün tersine (90°)
    home_relay_pin: int = 3           # GPIO3 (fiziksel pin 5) → IN2: saat yönünde (home)
    relay_active_low: bool = True     # Modül IN pini LOW olunca çeker
    relay_dead_time_seconds: float = 0.5  # Yön değişiminde iki röle arasındaki bekleme
    auto_home_seconds: float = 10.0  # Platform dönmüşken bu kadar süre araç görünmezse home'a dön
    # Bir hareket bu süre içinde hedefe varmazsa (switch arızası, sıkışma) acil durdurulur
    motion_timeout_seconds: float = 20.0


@dataclass(frozen=True)
class PhotoConfig:
    directory: str = "photos"             # photos/2026-11-04/14-32-05-123_<olay>.jpg
    retention_days: int = 30              # Daha eski fotoğraf klasörleri açılışta silinir
    unsafe_cooldown_seconds: float = 10.0  # Güvensiz durum fotoğrafları arasında en az bu kadar


@dataclass(frozen=True)
class IrRemoteConfig:
    enabled: bool = True
    driver_name: str = "gpio_ir_recv"  # gpio-ir sürücüsü; LIRC aygıtı buna göre bulunur
    # NEC tarama kodları (bu tip 17 tuşlu kumandalar için yaygın değerler).
    # Farklıysa terminalde "Tanımsız IR kodu geldi: 0x.." satırından okuyup buraya yazın.
    rotate_code: int = 0x1C     # OK
    emergency_code: int = 0x16  # *
    reset_code: int = 0x0D      # #
    repeat_suppress_seconds: float = 0.4  # Basılı tutunca gelen tekrarları yok say


@dataclass(frozen=True)
class KeyboardConfig:
    rotate_key: str = "d"
    emergency_key: str = "x"   # Acil durdur (kumandada *)
    reset_key: str = "r"       # Acil durdurmayı sıfırla (kumandada #)
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
    ir_remote: IrRemoteConfig = field(default_factory=IrRemoteConfig)
    photos: PhotoConfig = field(default_factory=PhotoConfig)
    log_file: str = "logs/platform.log"  # Her gece yeni dosyaya geçilir (platform.log.2026-11-04)
    log_retention_days: int = 30
