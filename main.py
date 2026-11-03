"""Araç döndürme platformu (basit sürüm) giriş noktası.

Kullanım:  python3 main.py
Tuşlar  :  d = döndür, q = çıkış, k = bölgeyi kaydet
           + / - (ya da b / v) = bölgeyi büyüt / küçült
           ok tuşları (ya da i / j / l / m) = bölgeyi taşı
"""
from __future__ import annotations

import logging
import threading
from typing import Callable
from contextlib import ExitStack
from pathlib import Path

from application.fps_meter import FpsMeter
from application.platform_controller import PlatformController
from application.zone_store import ZoneStore
from config import AppConfig
from domain.detection import LabelClassifier
from domain.geometry import Point
from domain.safety import SafetyChecker
from domain.zones import CircularZone
from hardware.imx500_detector import Imx500Detector
from hardware.indicators import ConsoleStatusIndicator, GpioStatusIndicator
from hardware.json_zone_repository import JsonZoneRepository
from hardware.keyboard_listener import KeyBindings, KeyboardListener
from hardware.simulated_button import SimulatedButton
from hardware.simulated_motor import SimulatedMotor
from presentation.composite_display import CompositeDisplay
from presentation.console_display import ConsoleDisplay

logger = logging.getLogger("platform")


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


def build_key_bindings(
    config: AppConfig, button: SimulatedButton, zone_store: ZoneStore, quit_event: threading.Event
) -> KeyBindings:
    keys = config.keyboard
    move = config.safety.zone_move_step
    resize = config.safety.zone_resize_step
    bindings: dict[str, Callable[[], None]] = {
        keys.rotate_key: button.press,
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


def build_indicator(config: AppConfig):
    try:
        return GpioStatusIndicator(config.gpio)
    except Exception as error:  # GPIO yoksa sistem yine de çalışsın
        logger.warning("GPIO kullanılamıyor (%s); göstergeler ekrana yazılacak.", error)
        return ConsoleStatusIndicator()


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
        f"'{keys.rotate_key}' = döndür | '{keys.quit_key}' = çıkış | "
        f"'{keys.save_zone_key}' = bölgeyi kaydet\n"
        f"Büyüt: {_join(keys.grow_keys)} | Küçült: {_join(keys.shrink_keys)}\n"
        f"Taşı: yukarı {_join(keys.up_keys)}, aşağı {_join(keys.down_keys)}, "
        f"sol {_join(keys.left_keys)}, sağ {_join(keys.right_keys)}"
    )


def _join(keys: tuple[str, ...]) -> str:
    return " / ".join(keys)


def main() -> None:
    config = AppConfig()
    configure_logging(config.log_file)

    classifier = LabelClassifier(config.safety.vehicle_labels, config.safety.living_labels)
    zone_store = build_zone_store(config)
    safety_checker = SafetyChecker(zone_store)
    display, overlay = build_displays(config, zone_store)
    button = SimulatedButton()
    quit_event = threading.Event()

    with ExitStack() as resources:
        detector = Imx500Detector(
            config.camera, classifier, frame_callback=overlay.draw if overlay else None
        )
        resources.callback(detector.close)

        indicator = build_indicator(config)
        resources.callback(indicator.close)

        listener = KeyboardListener(build_key_bindings(config, button, zone_store, quit_event))
        resources.callback(listener.close)

        controller = PlatformController(
            detector=detector,
            safety_checker=safety_checker,
            motor=SimulatedMotor(config.motor.rotation_seconds),
            button=button,
            indicator=indicator,
            display=display,
            fps_meter=FpsMeter(),
        )

        print_help(config)
        try:
            controller.run(should_stop=quit_event.is_set)
        except KeyboardInterrupt:
            pass
        logger.info("Sistem kapatılıyor.")


if __name__ == "__main__":
    main()
