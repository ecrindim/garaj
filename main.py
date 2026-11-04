"""Araç döndürme platformu (basit sürüm) giriş noktası.

Kullanım:  python3 main.py
Kumanda :  OK = döndür, * = acil durdur, # = acil durdurmayı sıfırla
Tuşlar  :  d = döndür, x = acil durdur, r = sıfırla, q = çıkış, k = bölgeyi kaydet
           + / - (ya da b / v) = bölgeyi büyüt / küçült
           ok tuşları (ya da i / j / l / m) = bölgeyi taşı
"""
from __future__ import annotations

import logging
import sys
import threading
from dataclasses import dataclass
from typing import Callable
from contextlib import ExitStack
from pathlib import Path

from application.fps_meter import FpsMeter
from application.platform_controller import PlatformController
from application.platform_motor import PlatformMotor
from application.vehicle_absence_timer import VehicleAbsenceTimer
from application.zone_store import ZoneStore
from config import AppConfig
from domain.detection import LabelClassifier
from domain.geometry import Point
from domain.safety import SafetyChecker
from domain.zones import CircularZone
from hardware.console_motor_driver import ConsoleMotorDriver
from hardware.imx500_detector import Imx500Detector
from hardware.indicators import ConsoleStatusIndicator, GpioStatusIndicator
from hardware.json_zone_repository import JsonZoneRepository
from hardware.keyboard_listener import KeyBindings, KeyboardListener
from hardware.proximity_sensor import ProximityPositionSensor
from hardware.event_button import EventButton
from hardware.ir_remote_listener import IrRemoteListener
from hardware.simulated_motor import SimulatedMotor
from presentation.composite_display import CompositeDisplay
from presentation.console_display import ConsoleDisplay

logger = logging.getLogger("platform")


def configure_console_encoding() -> None:
    """Terminalin dil ayarı UTF-8 olmasa da Türkçe karakterler doğru görünsün."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def configure_logging(log_file: str) -> None:
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(log_file, encoding="utf-8")],
    )


def build_zone_store(config: AppConfig) -> ZoneStore:
    width, height = config.camera.frame_size
    aspect_ratio = width / height
    repository = JsonZoneRepository(config.safety.zone_file, aspect_ratio)
    default_zone = CircularZone(
        center=Point(config.safety.zone_center_x, config.safety.zone_center_y),
        radius=config.safety.zone_radius,
        aspect_ratio=aspect_ratio,
    )
    saved_zone = repository.load()
    if saved_zone is not None:
        logger.info("Kayıtlı güvenli bölge yüklendi: %s", config.safety.zone_file)
    return ZoneStore(saved_zone or default_zone, repository)


@dataclass(frozen=True)
class ControlButtons:
    """Klavye ve kumandanın ortak bastığı düğmeler."""

    rotate: EventButton
    emergency: EventButton
    reset: EventButton


def build_key_bindings(
    config: AppConfig,
    buttons: ControlButtons,
    zone_store: ZoneStore,
    quit_event: threading.Event,
) -> KeyBindings:
    keys = config.keyboard
    move = config.safety.zone_move_step
    resize = config.safety.zone_resize_step
    bindings: dict[str, Callable[[], None]] = {
        keys.rotate_key: buttons.rotate.press,
        keys.emergency_key: buttons.emergency.press,
        keys.reset_key: buttons.reset.press,
        keys.quit_key: quit_event.set,
        keys.save_zone_key: zone_store.save,
    }
    zone_actions = [
        (keys.grow_keys, lambda: zone_store.resize(+resize)),
        (keys.shrink_keys, lambda: zone_store.resize(-resize)),
        (keys.up_keys, lambda: zone_store.move(0, -move)),
        (keys.down_keys, lambda: zone_store.move(0, +move)),
        (keys.left_keys, lambda: zone_store.move(-move, 0)),
        (keys.right_keys, lambda: zone_store.move(+move, 0)),
    ]
    for key_group, action in zone_actions:
        for key in key_group:
            bindings[key] = action
    return bindings


def start_ir_remote(config: AppConfig, buttons: ControlButtons, resources: ExitStack) -> None:
    ir = config.ir_remote
    if not ir.enabled:
        return
    bindings = {
        ir.rotate_code: buttons.rotate.press,
        ir.emergency_code: buttons.emergency.press,
        ir.reset_code: buttons.reset.press,
    }
    try:
        listener = IrRemoteListener(ir.driver_name, bindings, ir.repeat_suppress_seconds)
    except Exception as error:  # Kumanda yoksa sistem klavyeyle çalışmaya devam etsin
        logger.warning("IR kumanda kullanılamıyor (%s); sadece klavye çalışacak.", error)
        return
    resources.callback(listener.close)


def build_indicator(config: AppConfig):
    try:
        return GpioStatusIndicator(config.gpio)
    except Exception as error:  # GPIO yoksa sistem yine de çalışsın
        logger.warning("GPIO kullanılamıyor (%s); göstergeler ekrana yazılacak.", error)
        return ConsoleStatusIndicator()


def build_motor(config: AppConfig, resources: ExitStack):
    motor_config = config.motor
    if not motor_config.use_position_sensor:
        logger.info("Motor tam simülasyonda (90° süreyle kabul ediliyor).")
        return SimulatedMotor(motor_config.rotation_seconds)

    sensor = ProximityPositionSensor(motor_config.position_sensor_pin)
    resources.callback(sensor.close)
    logger.info("90° konumu E18-D80NK sensöründen okunuyor (GPIO%d).", motor_config.position_sensor_pin)
    return PlatformMotor(ConsoleMotorDriver(), sensor, motor_config.home_seconds)


def build_displays(config: AppConfig, zone_store: ZoneStore):
    displays = [ConsoleDisplay()]
    overlay = None
    if config.camera.show_preview:
        from presentation.preview_overlay import PreviewOverlay

        overlay = PreviewOverlay(zone_store)
        displays.append(overlay)
    return CompositeDisplay(displays), overlay


def print_help(config: AppConfig) -> None:
    keys = config.keyboard
    print(
        "Kumanda: OK = döndür | * = acil durdur | # = sıfırla\n"
        f"Klavye : '{keys.rotate_key}' = döndür | '{keys.emergency_key}' = acil durdur | "
        f"'{keys.reset_key}' = sıfırla | '{keys.quit_key}' = çıkış | "
        f"'{keys.save_zone_key}' = bölgeyi kaydet\n"
        f"Büyüt: {_join(keys.grow_keys)} | Küçült: {_join(keys.shrink_keys)}\n"
        f"Taşı: yukarı {_join(keys.up_keys)}, aşağı {_join(keys.down_keys)}, "
        f"sol {_join(keys.left_keys)}, sağ {_join(keys.right_keys)}"
    )


def _join(keys: tuple[str, ...]) -> str:
    return " / ".join(keys)


def main() -> None:
    configure_console_encoding()
    config = AppConfig()
    configure_logging(config.log_file)

    classifier = LabelClassifier(config.safety.vehicle_labels, config.safety.living_labels)
    zone_store = build_zone_store(config)
    safety_checker = SafetyChecker(zone_store)
    display, overlay = build_displays(config, zone_store)
    buttons = ControlButtons(rotate=EventButton(), emergency=EventButton(), reset=EventButton())
    quit_event = threading.Event()

    with ExitStack() as resources:
        detector = Imx500Detector(
            config.camera, classifier, frame_callback=overlay.draw if overlay else None
        )
        resources.callback(detector.close)

        indicator = build_indicator(config)
        resources.callback(indicator.close)

        listener = KeyboardListener(build_key_bindings(config, buttons, zone_store, quit_event))
        resources.callback(listener.close)

        start_ir_remote(config, buttons, resources)

        controller = PlatformController(
            detector=detector,
            safety_checker=safety_checker,
            motor=build_motor(config, resources),
            button=buttons.rotate,
            indicator=indicator,
            display=display,
            fps_meter=FpsMeter(),
            absence_timer=VehicleAbsenceTimer(config.motor.auto_home_seconds),
            emergency_button=buttons.emergency,
            reset_button=buttons.reset,
            motion_timeout_seconds=config.motor.motion_timeout_seconds,
        )

        print_help(config)
        try:
            controller.run(should_stop=quit_event.is_set)
        except KeyboardInterrupt:
            pass
        logger.info("Sistem kapatılıyor.")


if __name__ == "__main__":
    main()
