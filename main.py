"""Araç döndürme platformu (basit sürüm) giriş noktası.

Kullanım:  python3 main.py
Tuşlar  :  d = döndür düğmesi, q = çıkış
"""
from __future__ import annotations

import logging
from contextlib import ExitStack
from pathlib import Path

from application.platform_controller import PlatformController
from config import AppConfig
from domain.detection import LabelClassifier
from domain.safety import SafetyChecker
from hardware.imx500_detector import Imx500Detector
from hardware.indicators import ConsoleStatusIndicator, GpioStatusIndicator
from hardware.keyboard_button import KeyboardButton
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


def build_indicator(config: AppConfig):
    try:
        return GpioStatusIndicator(config.gpio)
    except Exception as error:  # GPIO yoksa sistem yine de çalışsın
        logger.warning("GPIO kullanılamıyor (%s); göstergeler ekrana yazılacak.", error)
        return ConsoleStatusIndicator()


def build_displays(config: AppConfig):
    displays = [ConsoleDisplay()]
    overlay = None
    if config.camera.show_preview:
        from presentation.preview_overlay import PreviewOverlay

        overlay = PreviewOverlay(config.safety.safe_zone)
        displays.append(overlay)
    return CompositeDisplay(displays), overlay


def main() -> None:
    config = AppConfig()
    configure_logging(config.log_file)

    classifier = LabelClassifier(config.safety.vehicle_labels, config.safety.living_labels)
    safety_checker = SafetyChecker(config.safety.safe_zone)
    display, overlay = build_displays(config)

    with ExitStack() as resources:
        detector = Imx500Detector(
            config.camera, classifier, frame_callback=overlay.draw if overlay else None
        )
        resources.callback(detector.close)

        indicator = build_indicator(config)
        resources.callback(indicator.close)

        button = KeyboardButton(config.keyboard.rotate_key, config.keyboard.quit_key)
        resources.callback(button.close)

        controller = PlatformController(
            detector=detector,
            safety_checker=safety_checker,
            motor=SimulatedMotor(config.motor.rotation_seconds),
            button=button,
            indicator=indicator,
            display=display,
        )

        print(f"'{config.keyboard.rotate_key}' = döndür, '{config.keyboard.quit_key}' = çıkış")
        try:
            controller.run(should_stop=lambda: button.quit_requested)
        except KeyboardInterrupt:
            pass
        logger.info("Sistem kapatılıyor.")


if __name__ == "__main__":
    main()
