"""Gerçek platform motorunun konum mantığı (iki mekanik limit switch ile).

- Home switch'i basılı      → HOME
- 90° switch'i basılı       → DÖNMÜŞ
- İkisi de bırakık          → ARADA (hareket sürüyor ya da yarıda kesildi)
- İkisi de basılı           → ARIZA (kablo kısa devresi ya da switch arızası)

Panodaki switch'ler motoru uçlarda zaten keser; bu sınıf Pi'nin hareketin
bittiğini kesin olarak bilmesini ve arızayı fark etmesini sağlar:
motor çalıştırıldıktan `departure_timeout_seconds` sonra platform hâlâ
başlangıç switch'inden ayrılmadıysa motor dönmüyor demektir.

Motor komutları `MotorDriver` üzerinden verilir (röle ya da ekrana yazı).
"""
from __future__ import annotations

import time
from typing import Callable, Optional

from application.ports import MotorDriver, PlatformPosition, PositionSwitch

END_POSITIONS = (PlatformPosition.HOME, PlatformPosition.ROTATED)


class PlatformMotor:
    def __init__(
        self,
        driver: MotorDriver,
        home_switch: PositionSwitch,
        rotated_switch: PositionSwitch,
        departure_timeout_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._driver = driver
        self._home_switch = home_switch
        self._rotated_switch = rotated_switch
        self._departure_timeout_seconds = departure_timeout_seconds
        self._clock = clock
        self._target: Optional[PlatformPosition] = None
        self._start_position = PlatformPosition.BETWEEN
        self._started_at = 0.0

    @property
    def position(self) -> PlatformPosition:
        at_home = self._home_switch.is_triggered()
        at_rotated = self._rotated_switch.is_triggered()
        if at_home and at_rotated:
            return PlatformPosition.FAULT
        if at_home:
            return PlatformPosition.HOME
        if at_rotated:
            return PlatformPosition.ROTATED
        return PlatformPosition.BETWEEN

    def rotate_out(self) -> None:
        self._begin(PlatformPosition.ROTATED)
        self._driver.start_rotate_out()

    def return_home(self) -> None:
        self._begin(PlatformPosition.HOME)
        self._driver.start_return_home()

    def stop(self) -> None:
        self._driver.stop()
        self._target = None

    def has_reached_target(self) -> bool:
        return self._target is not None and self.position is self._target

    def failed_to_depart(self) -> bool:
        if self._target is None or self._start_position not in END_POSITIONS:
            return False  # Aradan başlayan harekette ayrılınacak bir switch yok
        elapsed = self._clock() - self._started_at
        return elapsed >= self._departure_timeout_seconds and self.position is self._start_position

    def _begin(self, target: PlatformPosition) -> None:
        self._start_position = self.position
        self._target = target
        self._started_at = self._clock()
