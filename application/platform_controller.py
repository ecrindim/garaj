"""Platformun iki durumlu (DURUYOR / DÖNÜYOR) kontrol akışı."""
from __future__ import annotations

import logging
from typing import Callable

from application.ports import (
    CommandButton,
    ObjectDetector,
    PlatformState,
    RotationMotor,
    StatusDisplay,
    StatusIndicator,
    StatusSnapshot,
)
from domain.safety import SafetyChecker, SafetyReport

logger = logging.getLogger(__name__)


class PlatformController:
    def __init__(
        self,
        detector: ObjectDetector,
        safety_checker: SafetyChecker,
        motor: RotationMotor,
        button: CommandButton,
        indicator: StatusIndicator,
        display: StatusDisplay,
    ) -> None:
        self._detector = detector
        self._safety = safety_checker
        self._motor = motor
        self._button = button
        self._indicator = indicator
        self._display = display
        self._state = PlatformState.IDLE
        self._rotate_command = 0

    def run(self, should_stop: Callable[[], bool]) -> None:
        self._indicator.show_idle()
        logger.info("Sistem hazır. Platform duruyor, kırmızı LED yanıyor.")
        while not should_stop():
            self.step()

    def step(self) -> None:
        detections = self._detector.read_detections()
        report = self._safety.evaluate(detections)
        button_pressed = self._button.was_pressed()

        if self._state is PlatformState.IDLE:
            self._handle_idle(button_pressed, report)
        else:
            self._handle_rotating(button_pressed, report)

        self._display.update(
            StatusSnapshot(self._state, button_pressed, self._rotate_command, report, detections)
        )

    def _handle_idle(self, button_pressed: bool, report: SafetyReport) -> None:
        if not button_pressed:
            return
        logger.info("Döndürme düğmesine basıldı.")
        if report.is_safe:
            self._start_rotation()
        else:
            logger.warning("Döndürme reddedildi: %s", report.status.value)

    def _handle_rotating(self, button_pressed: bool, report: SafetyReport) -> None:
        if button_pressed:
            logger.info("Platform zaten dönüyor, düğme yok sayıldı.")
        if report.living_nearby:
            logger.warning("Dönüş sırasında canlı algılandı, platform durduruluyor!")
            self._stop_rotation()
        elif self._motor.is_rotation_complete():
            logger.info("Döndürme tamamlandı.")
            self._stop_rotation()

    def _start_rotation(self) -> None:
        self._rotate_command = 1
        self._state = PlatformState.ROTATING
        self._motor.start_rotation()
        self._indicator.show_rotating()
        logger.info("DÖNDÜR KOMUTU = 1")

    def _stop_rotation(self) -> None:
        self._rotate_command = 0
        self._state = PlatformState.IDLE
        self._motor.stop()
        self._indicator.show_idle()
        logger.info("DÖNDÜR KOMUTU = 0")
