"""Platformun kontrol akışı.

Durumlar : DURUYOR, DÖNÜYOR, HOME'A DÖNÜYOR
Konumlar : HOME, DÖNMÜŞ, ARADA

Araç hem garaja girerken hem çıkarken platform aynı yönde (saat yönünün
tersine) 90° döner; araç her iki durumda da geri geri hareket eder.

- Düğme, platform home'da ya da aradayken: araç güvenli bölgedeyse 90° döndür.
- Düğme, platform dönmüşken: platformu araçla birlikte home'a döndür.
- Platform home'da değilken kamerada belirli süre araç görünmezse home'a dön
  (araç garaja girdikten de garajdan çıktıktan da sonra).
- Hareket sırasında canlı görülürse motor durur.
- Acil durdur (kumandada *): motor durur ve sistem KİLİTLENİR. Sıfırlama
  (kumandada #) yapılana kadar döndürme ve otomatik home çalışmaz.
- Bir hareket `motion_timeout_seconds` içinde hedefe varmazsa (sensör
  arızası, sıkışma) sistem aynı şekilde acil durdurulur.
"""
from __future__ import annotations

import logging
import time
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
        emergency_button: CommandButton,
        reset_button: CommandButton,
        motion_timeout_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._detector = detector
        self._safety = safety_checker
        self._motor = motor
        self._button = button
        self._indicator = indicator
        self._display = display
        self._fps_meter = fps_meter
        self._absence_timer = absence_timer
        self._emergency_button = emergency_button
        self._reset_button = reset_button
        self._motion_timeout_seconds = motion_timeout_seconds
        self._clock = clock
        self._motion_started_at = 0.0
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
        # Tüm düğmeler her karede okunur ki eski basışlar birikip sonradan tetiklenmesin
        button_pressed = self._button.was_pressed()
        emergency_pressed = self._emergency_button.was_pressed()
        reset_pressed = self._reset_button.was_pressed()

        if emergency_pressed:
            self._enter_emergency("Acil durdur butonuna basıldı")
        elif self._state is PlatformState.EMERGENCY_STOPPED:
            self._handle_emergency(button_pressed, reset_pressed)
        elif self._state is PlatformState.IDLE:
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
        if not report.is_safe:
            logger.warning("Döndürme reddedildi: %s", report.status.value)
            return
        self._begin_motion(PlatformState.ROTATING, MotorCommand.ROTATE)
        self._motor.rotate_out()
        logger.info("DÖNDÜR KOMUTU = 1")

    def _try_return_home(self, report: SafetyReport) -> None:
        if report.living_nearby:
            logger.warning("Home dönüşü reddedildi: %s", report.status.value)
            return
        self._begin_motion(PlatformState.RETURNING_HOME, MotorCommand.HOME)
        self._motor.return_home()
        logger.info("HOME KOMUTU = 1")

    # --- acil durdurma ----------------------------------------------------

    def _enter_emergency(self, reason: str) -> None:
        logger.error("ACİL DURDURMA: %s. Sıfırlamak için # tuşuna basın.", reason)
        self._motor.stop()
        self._state = PlatformState.EMERGENCY_STOPPED
        self._command = MotorCommand.NONE
        self._absence_timer.reset()
        self._indicator.show_emergency()

    def _handle_emergency(self, button_pressed: bool, reset_pressed: bool) -> None:
        if reset_pressed:
            logger.info("Acil durdurma sıfırlandı, sistem normal çalışmaya döndü.")
            self._state = PlatformState.IDLE
            self._indicator.show_idle()
        elif button_pressed:
            logger.warning("Acil durdurma aktif, döndürme yapılamaz. Önce # ile sıfırlayın.")

    # --- hareket halindeyken ---------------------------------------------

    def _handle_moving(self, button_pressed: bool, report: SafetyReport) -> None:
        if button_pressed:
            logger.info("Platform hareket halinde, düğme yok sayıldı.")
        if report.living_nearby:
            logger.warning("Hareket sırasında canlı algılandı, platform durduruluyor!")
            self._stop_motion()
        elif self._motor.has_reached_target():
            self._on_target_reached()
        elif self._motion_timed_out():
            self._enter_emergency(
                f"Hedefe {self._motion_timeout_seconds:.0f} sn içinde varılamadı "
                "(sensör arızası ya da sıkışma olabilir)"
            )

    def _motion_timed_out(self) -> bool:
        return self._clock() - self._motion_started_at >= self._motion_timeout_seconds

    def _on_target_reached(self) -> None:
        if self._state is PlatformState.ROTATING:
            logger.info("Dönüş tamamlandı, platform 90° konumunda.")
        else:
            logger.info("Platform home konumunda.")
        self._stop_motion()

    # --- motor komutları -------------------------------------------------

    def _begin_motion(self, state: PlatformState, command: MotorCommand) -> None:
        self._state = state
        self._command = command
        self._motion_started_at = self._clock()
        self._absence_timer.reset()
        self._indicator.show_rotating()

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
