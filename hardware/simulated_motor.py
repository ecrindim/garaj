"""Gerçek motor gelene kadar platformun hareketini simüle eder.

Limit switch'ler takılmadan önce kullanılır. Platformun home'dan uzaklığı
0..1 arasında tutulur ve süreye göre ilerler; hareket yarıda kesilirse konum
korunur. Komutlar verilen `MotorDriver`'a iletilir: röleler bağlıysa gerçek
motor da döner (switch'ler gelmeden röle/pano bağlantısını test etmek için).
"""
from __future__ import annotations

import logging
import time
from typing import Callable, Optional

from application.ports import MotorDriver, PlatformPosition

logger = logging.getLogger(__name__)

HOME_PROGRESS = 0.0
ROTATED_PROGRESS = 1.0


class SimulatedMotor:
    def __init__(
        self,
        rotation_seconds: float,
        driver: MotorDriver,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._rotation_seconds = rotation_seconds
        self._driver = driver
        self._clock = clock
        self._progress = HOME_PROGRESS
        self._target: Optional[float] = None
        self._last_update = clock()

    @property
    def position(self) -> PlatformPosition:
        self._advance()
        if self._progress <= HOME_PROGRESS:
            return PlatformPosition.HOME
        if self._progress >= ROTATED_PROGRESS:
            return PlatformPosition.ROTATED
        return PlatformPosition.BETWEEN

    def rotate_out(self) -> None:
        self._start(ROTATED_PROGRESS)
        logger.info("Simülasyon: 90°'ye dönüş başladı (konum %%%d)", self._percent())
        self._driver.start_rotate_out()

    def return_home(self) -> None:
        self._start(HOME_PROGRESS)
        logger.info("Simülasyon: home'a dönüş başladı (konum %%%d)", self._percent())
        self._driver.start_return_home()

    def stop(self) -> None:
        self._advance()
        self._target = None
        self._driver.stop()
        logger.info("Simülasyon: durdu (konum %%%d)", self._percent())

    def failed_to_depart(self) -> bool:
        return False  # Simülasyonda motor her zaman hareket eder

    def has_reached_target(self) -> bool:
        self._advance()
        return self._target is not None and self._progress == self._target

    def _start(self, target: float) -> None:
        self._advance()
        self._target = target
        self._last_update = self._clock()

    def _advance(self) -> None:
        now = self._clock()
        if self._target is not None:
            step = (now - self._last_update) / self._rotation_seconds
            if self._target > self._progress:
                self._progress = min(self._target, self._progress + step)
            else:
                self._progress = max(self._target, self._progress - step)
        self._last_update = now

    def _percent(self) -> int:
        return round(self._progress * 100)
