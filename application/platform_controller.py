"""Platformun kontrol akışı.

Durumlar : DURUYOR, DÖNÜYOR, HOME'A DÖNÜYOR, ACİL DURDURULDU
Konumlar : HOME, DÖNMÜŞ, ARADA

Araç hem garaja girerken hem çıkarken platform aynı yönde (saat yönünün
tersine) 90° döner; iş bitince saat yönünde home'a geri gelir.

Düğme (kumandada OK):
- Platform home'dayken: araç güvenli bölgede ve çevrede canlı yoksa 90° döndür.
- Platform dönmüşken: platformu araçla birlikte home'a döndür.
- Platform aradayken (hareket yarıda kesildiyse): kesilen hareketi sürdür.
  Dönüş için normal döndürme şartları aranır (güvenli bölge daire, yarı dönmüş
  araç kutusu da sığacak şekilde ayarlanır; taşıyorsa bir sorun vardır).
- Home'a dönüşlerde (düğme, devam, reset sonrası) çevrede canlı olmamalı ve
  platformda araç varsa güvenli bölgenin sınırını aşmamalı.

Otomatik:
- Platform home'da değilken kamerada belirli süre araç görünmezse home'a dön.
- Hareket sırasında canlı görülürse motor durur. Araç konumu hareket
  sırasında kontrol edilmez (dönen aracın kutusu daireden taşabilir).

Acil durdurma (kumandada *): motor durur, sistem kilitlenir. Sıfırlama
(kumandada #) sonrası platform home'a döner (çevrede canlı yoksa).
Bir hareket `motion_timeout_seconds` içinde hedefe varmazsa da acil durdurulur.

Fotoğraf: dönüş onaylanınca, araç platformdayken döndürme reddedilince,
araç platformdayken çevrede canlı belirince ve dönüş tamamlanınca.
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
    PhotoEvent,
    PhotoRecorder,
    PlatformPosition,
    PlatformState,
    RotationMotor,
    StatusDisplay,
    StatusIndicator,
    StatusSnapshot,
)
from application.unsafe_situation_watcher import UnsafeSituationWatcher
from application.vehicle_absence_timer import VehicleAbsenceTimer
from domain.detection import Detection
from domain.safety import SafetyChecker, SafetyReport

logger = logging.getLogger(__name__)

MOVING_STATES = (PlatformState.ROTATING, PlatformState.RETURNING_HOME)


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
        photo_recorder: PhotoRecorder,
        unsafe_watcher: UnsafeSituationWatcher,
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
        self._photos = photo_recorder
        self._unsafe_watcher = unsafe_watcher
        self._clock = clock
        self._state = PlatformState.IDLE
        self._command = MotorCommand.NONE
        self._motion_started_at = 0.0
        self._interrupted_motion: Optional[PlatformState] = None
        self._home_pending_after_reset = False
        self._home_wait_logged = False

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

        self._watch_unsafe_situation(report)
        self._display.update(self._snapshot(button_pressed, report, detections, fps))

    # --- duruyorken ------------------------------------------------------

    def _handle_idle(self, button_pressed: bool, report: SafetyReport, detections: Sequence[Detection]) -> None:
        if self._home_pending_after_reset:
            self._continue_pending_home(button_pressed, report)
        elif button_pressed:
            self._handle_button(report)
        else:
            self._check_auto_home(report, detections)

    def _handle_button(self, report: SafetyReport) -> None:
        logger.info("Döndürme düğmesine basıldı.")
        position = self._motor.position
        if position is PlatformPosition.ROTATED:
            self._try_return_home(report)
        elif position is PlatformPosition.BETWEEN:
            self._try_resume(report)
        else:
            self._try_rotate(report)

    def _continue_pending_home(self, button_pressed: bool, report: SafetyReport) -> None:
        if button_pressed:
            logger.info("Sıfırlama sonrası önce home'a dönülecek, düğme yok sayıldı.")
        if self._motor.position is PlatformPosition.HOME:
            self._home_pending_after_reset = False
        elif report.clear_for_home:
            self._home_pending_after_reset = False
            self._home_wait_logged = False
            logger.info("Sıfırlama sonrası platform home'a dönüyor.")
            self._start_return_home()
        elif not self._home_wait_logged:
            self._home_wait_logged = True
            logger.warning("Sıfırlama sonrası home dönüşü bekliyor: %s", report.status.value)

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
            if _vehicle_present(report):
                self._photos.capture(PhotoEvent.ROTATION_REJECTED)
            return
        self._photos.capture(PhotoEvent.ROTATION_APPROVED)
        self._start_rotation()

    def _try_resume(self, report: SafetyReport) -> None:
        resuming_home = self._interrupted_motion is PlatformState.RETURNING_HOME
        allowed = report.clear_for_home if resuming_home else report.is_safe
        if not allowed:
            logger.warning("Devam reddedildi: %s", report.status.value)
            if _vehicle_present(report):
                self._photos.capture(PhotoEvent.ROTATION_REJECTED)
            return
        if resuming_home:
            logger.info("Yarıda kalan home dönüşü sürdürülüyor.")
            self._start_return_home()
        else:
            logger.info("Yarıda kalan dönüş sürdürülüyor.")
            self._photos.capture(PhotoEvent.ROTATION_APPROVED)
            self._start_rotation()

    def _try_return_home(self, report: SafetyReport) -> None:
        if not report.clear_for_home:
            logger.warning("Home dönüşü reddedildi: %s", report.status.value)
            if _vehicle_present(report):
                self._photos.capture(PhotoEvent.ROTATION_REJECTED)
            return
        self._start_return_home()

    # --- hareket halindeyken ---------------------------------------------

    def _handle_moving(self, button_pressed: bool, report: SafetyReport) -> None:
        if button_pressed:
            logger.info("Platform hareket halinde, düğme yok sayıldı.")
        if report.living_nearby:
            logger.warning("Hareket sırasında canlı algılandı, platform durduruluyor!")
            self._interrupted_motion = self._state
            self._stop_motion()
        elif self._motor.has_reached_target():
            self._on_target_reached()
        elif self._motion_timed_out():
            self._enter_emergency(
                f"Hedefe {self._motion_timeout_seconds:.0f} sn içinde varılamadı "
                "(sensör arızası ya da sıkışma olabilir)"
            )

    def _on_target_reached(self) -> None:
        if self._state is PlatformState.ROTATING:
            logger.info("Dönüş tamamlandı, platform 90° konumunda.")
            self._photos.capture(PhotoEvent.ROTATION_COMPLETED)
        else:
            logger.info("Platform home konumunda.")
        self._interrupted_motion = None
        self._stop_motion()

    def _motion_timed_out(self) -> bool:
        return self._clock() - self._motion_started_at >= self._motion_timeout_seconds

    # --- acil durdurma ---------------------------------------------------

    def _enter_emergency(self, reason: str) -> None:
        logger.error("ACİL DURDURMA: %s. Sıfırlamak için # tuşuna basın.", reason)
        self._motor.stop()
        self._state = PlatformState.EMERGENCY_STOPPED
        self._command = MotorCommand.NONE
        self._absence_timer.reset()
        self._home_pending_after_reset = False
        self._indicator.show_emergency()

    def _handle_emergency(self, button_pressed: bool, reset_pressed: bool) -> None:
        if reset_pressed:
            logger.info("Acil durdurma sıfırlandı.")
            self._state = PlatformState.IDLE
            self._interrupted_motion = None
            self._home_pending_after_reset = self._motor.position is not PlatformPosition.HOME
            if self._home_pending_after_reset:
                logger.info("Platform home'a dönecek (çevrede canlı yoksa).")
            self._indicator.show_idle()
        elif button_pressed:
            logger.warning("Acil durdurma aktif, döndürme yapılamaz. Önce # ile sıfırlayın.")

    # --- fotoğraf ----------------------------------------------------------

    def _watch_unsafe_situation(self, report: SafetyReport) -> None:
        unsafe = _vehicle_present(report) and report.living_nearby
        if self._unsafe_watcher.update(unsafe):
            logger.warning("Araç platformdayken güvensiz durum: %s", report.status.value)
            self._photos.capture(PhotoEvent.UNSAFE_SITUATION)

    # --- motor komutları -------------------------------------------------

    def _start_rotation(self) -> None:
        self._begin_motion(PlatformState.ROTATING, MotorCommand.ROTATE)
        self._motor.rotate_out()
        logger.info("DÖNDÜR KOMUTU = 1")

    def _start_return_home(self) -> None:
        self._begin_motion(PlatformState.RETURNING_HOME, MotorCommand.HOME)
        self._motor.return_home()
        logger.info("HOME KOMUTU = 1")

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


def _vehicle_present(report: SafetyReport) -> bool:
    """Platformda (tamamen ya da kısmen) araç var mı?"""
    return report.vehicle_on_platform or report.vehicle_crossing
