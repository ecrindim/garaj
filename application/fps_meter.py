"""Döngünün saniyedeki kare (çıkarım) sayısını ölçer."""
from __future__ import annotations

import time
from typing import Callable, Optional


class FpsMeter:
    def __init__(self, window_seconds: float = 1.0, clock: Callable[[], float] = time.monotonic) -> None:
        self._window_seconds = window_seconds
        self._clock = clock
        self._window_start: Optional[float] = None
        self._frames = 0
        self._fps = 0.0

    def tick(self) -> float:
        """Her karede bir kez çağrılır; son ölçülen FPS değerini döner."""
        now = self._clock()
        if self._window_start is None:
            self._window_start = now
            return self._fps

        self._frames += 1
        elapsed = now - self._window_start
        if elapsed >= self._window_seconds:
            self._fps = self._frames / elapsed
            self._frames = 0
            self._window_start = now
        return self._fps
