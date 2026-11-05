"""Gerçek platform motorunun konum mantığı.

- 90° konumu : platform 90°'ye gelince mekanik limit switch'e basar.
- Home       : motoru panodaki mekanik switch keser; Pi switch'i okumaz,
               home komutundan `home_seconds` sonra home'a varılmış kabul eder.
- Ara konum  : bilinmez ve gerekmez. Yön her zaman belli (dışarı = saat yönünün
               tersi, home = saat yönü); motor hedefe varana kadar döner.

Motor komutları `MotorDriver` üzerinden verilir; şimdilik ekrana yazan sürücü,
röleler gelince röle sürücüsü kullanılır. Bu sınıf değişmez.
"""
from __future__ import annotations

import logging
import time
from typing import Callable, Optional

from application.ports import MotorDriver, PlatformPosition, RotatedPositionSensor

logger = logging.getLogger(__name__)


class PlatformMotor:
    def __init__(
        self,
        driver: MotorDriver,
        rotated_sensor: RotatedPositionSensor,
        home_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._driver = driver
        self._rotated_sensor = rotated_sensor
        self._home_seconds = home_seconds
        self._clock = clock
        self._at_home = True  # Açılışta platform home'da kabul edilir
        self._target: Optional[PlatformPosition] = None
        self._started_at = 0.0

    @property
    def position(self) -> PlatformPosition:
        if self._rotated_sensor.is_triggered():
            return PlatformPosition.ROTATED
        if self._at_home:
            return PlatformPosition.HOME
        return PlatformPosition.BETWEEN

    def rotate_out(self) -> None:
        self._at_home = False
        self._start(PlatformPosition.ROTATED)
        self._driver.start_rotate_out()

    def return_home(self) -> None:
        self._start(PlatformPosition.HOME)
        self._driver.start_return_home()

    def stop(self) -> None:
        self._driver.stop()
        self._target = None

    def has_reached_target(self) -> bool:
        if self._target is PlatformPosition.ROTATED:
            return self._rotated_sensor.is_triggered()
        if self._target is PlatformPosition.HOME and self._home_time_elapsed():
            self._at_home = True
            return True
        return False

    def _start(self, target: PlatformPosition) -> None:
        self._target = target
        self._started_at = self._clock()

    def _home_time_elapsed(self) -> bool:
        return self._clock() - self._started_at >= self._home_seconds
