"""Platformun kontrol akışı.

Durumlar : DURUYOR, DÖNÜYOR, HOME'A DÖNÜYOR
Konumlar : HOME, DÖNMÜŞ, ARADA

- Düğme, platform home'da (ya da arada) iken: araç güvenli bölgedeyse döndür.
- Düğme, platform dönmüşken: platformu home'a döndür (araçla birlikte).
- Platform home'da değilken kamerada belirli süre araç görünmezse: home'a dön.
- Hareket sırasında canlı görülürse motor durur. Araç konumu hareket
  sırasında kontrol edilmez (dönen aracın kutusu daireden taşabilir).
"""
from __future__ import annotations

import logging
from typing import Callable, Optional, Sequence

from application.fps_meter import FpsMeter
from application.ports import (
    CommandButton,
    MotorCommand,
    ObjectDetector,
    PlatformPosition,
    PlatformState,
    RotationMotor,
    StatusDisplay,
    StatusIndicator,
    StatusSnapshot,
)
from application.vehicle_absence_timer import VehicleAbsenceTimer
from domain.detection import Detection
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
        fps_meter: FpsMeter,
        absence_timer: VehicleAbsenceTimer,
    ) -> None:
        self._detector = detector
        self._safety = safety_checker
        self._motor = motor
        self._button = button
        self._indicator = indicator
        self._display = display
        self._fps_meter = fps_meter
        self._absence_timer = absence_timer
        self._state = PlatformState.IDLE
        self._command = MotorCommand.NONE

    def run(self, should_stop: Callable[[], bool]) -> None:
        self._indicator.show_idle()
        logger.info("Sistem hazır. Platform duruyor, kırmızı LED yanıyor.")
        while not should_stop():
            self.step()

    def step(self) -> None:
        detections = self._detector.read_detections()
        fps = self._fps_meter.tick()
        report = self._safety.evaluate(detections)
        button_pressed = self._button.was_pressed()

        if self._state is PlatformState.IDLE:
            self._handle_idle(button_pressed, report, detections)
        else:
            self._handle_moving(button_pressed, report)

        self._display.update(self._snapshot(button_pressed, report, detections, fps))

    # --- duruyorken ------------------------------------------------------

    def _handle_idle(self, button_pressed: bool, report: SafetyReport, detections: Sequence[Detection]) -> None:
        if button_pressed:
            self._handle_button(report)
        else:
            self._check_auto_home(report, detections)

    def _handle_button(self, report: SafetyReport) -> None:
        logger.info("Döndürme düğmesine basıldı.")
        if self._motor.position is PlatformPosition.ROTATED:
            self._try_return_home(report)
        else:
            self._try_rotate(report)

    def _check_auto_home(self, report: SafetyReport, detections: Sequence[Detection]) -> None:
        if self._motor.position is PlatformPosition.HOME:
            self._absence_timer.reset()
            return
        vehicle_visible = any(d.is_vehicle for d in detections)
        if not self._absence_timer.update(vehicle_visible):
            return
        if report.living_nearby:
            return  # Canlı uzaklaşınca bir sonraki karede tekrar denenir
        logger.info("%.0f sn boyunca araç görünmedi.", self._absence_timer.timeout_seconds)
        self._try_return_home(report)

    def _try_rotate(self, report: SafetyReport) -> None:
        if report.is_safe:
            self._start_motion(PlatformState.ROTATING, PlatformPosition.ROTATED, MotorCommand.ROTATE)
        else:
            logger.warning("Döndürme reddedildi: %s", report.status.value)

    def _try_return_home(self, report: SafetyReport) -> None:
        if report.living_nearby:
            logger.warning("Home dönüşü reddedildi: %s", report.status.value)
            return
        self._start_motion(PlatformState.RETURNING_HOME, PlatformPosition.HOME, MotorCommand.HOME)

    # --- hareket halindeyken ---------------------------------------------

    def _handle_moving(self, button_pressed: bool, report: SafetyReport) -> None:
        if button_pressed:
            logger.info("Platform hareket halinde, düğme yok sayıldı.")
        if report.living_nearby:
            logger.warning("Hareket sırasında canlı algılandı, platform durduruluyor!")
            self._stop_motion()
        elif self._motor.has_reached_target():
            logger.info("Hedefe ulaşıldı: %s", self._motor.position.value)
            self._stop_motion()

    # --- motor komutları -------------------------------------------------

    def _start_motion(self, state: PlatformState, target: PlatformPosition, command: MotorCommand) -> None:
        self._state = state
        self._command = command
        self._absence_timer.reset()
        self._motor.rotate_to(target)
        self._indicator.show_rotating()
        logger.info("%s KOMUTU = 1", command.value)

    def _stop_motion(self) -> None:
        logger.info("%s KOMUTU = 0", self._command.value)
        self._state = PlatformState.IDLE
        self._command = MotorCommand.NONE
        self._absence_timer.reset()
        self._motor.stop()
        self._indicator.show_idle()

    def _snapshot(
        self, button_pressed: bool, report: SafetyReport, detections: Sequence[Detection], fps: float
    ) -> StatusSnapshot:
        return StatusSnapshot(
            state=self._state,
            position=self._motor.position,
            command=self._command,
            button_pressed=button_pressed,
            safety=report,
            detections=detections,
            fps=fps,
            seconds_until_home=self._seconds_until_home(),
        )

    def _seconds_until_home(self) -> Optional[float]:
        if self._state is not PlatformState.IDLE:
            return None
        return self._absence_timer.remaining_seconds()
