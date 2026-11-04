"""Gerçek motor gelene kadar platformun hareketini simüle eder.

Gerçek sistemde:
  - 90° dönüş (saat yönünün tersine): lazer sensör platform ucundaki
    metali görünce hedefe varılmış sayılır.
  - Home dönüşü (saat yönünde): motoru panodaki mekanik switch keser;
    Pi switch'i okumaz, belirli süre dolunca home'a varılmış kabul eder.

Simülasyonda platformun home'dan uzaklığı 0..1 arasında tutulur ve süreye
göre ilerler. Hareket yarıda kesilirse konum korunur.
"""
from __future__ import annotations

import logging
import time
from typing import Callable, Optional

from application.ports import PlatformPosition

logger = logging.getLogger(__name__)

HOME_PROGRESS = 0.0
ROTATED_PROGRESS = 1.0


class SimulatedMotor:
    def __init__(self, rotation_seconds: float, clock: Callable[[], float] = time.monotonic) -> None:
        self._rotation_seconds = rotation_seconds
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
        logger.info(">>> MOTOR DÖNÜYOR → 90° saat yönünün tersine (simülasyon, konum %%%d)", self._percent())

    def return_home(self) -> None:
        self._start(HOME_PROGRESS)
        logger.info(">>> MOTOR HOME'A DÖNÜYOR → saat yönünde (simülasyon, konum %%%d)", self._percent())

    def stop(self) -> None:
        self._advance()
        self._target = None
        logger.info(">>> MOTOR DURDU (konum %%%d)", self._percent())

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
