"""Kamerada kesintisiz olarak ne kadar süredir araç görünmediğini sayar.

Araç bir kare bile görünürse sayaç sıfırlanır.
"""
from __future__ import annotations

import time
from typing import Callable, Optional


class VehicleAbsenceTimer:
    def __init__(self, timeout_seconds: float, clock: Callable[[], float] = time.monotonic) -> None:
        self._timeout_seconds = timeout_seconds
        self._clock = clock
        self._absent_since: Optional[float] = None

    @property
    def timeout_seconds(self) -> float:
        return self._timeout_seconds

    def reset(self) -> None:
        self._absent_since = None

    def update(self, vehicle_visible: bool) -> bool:
        """Süre dolduysa True döner."""
        if vehicle_visible:
            self._absent_since = None
            return False
        if self._absent_since is None:
            self._absent_since = self._clock()
        return self._clock() - self._absent_since >= self._timeout_seconds

    def remaining_seconds(self) -> Optional[float]:
        if self._absent_since is None:
            return None
        elapsed = self._clock() - self._absent_since
        return max(0.0, self._timeout_seconds - elapsed)
