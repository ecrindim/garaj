"""Güvensiz bir durumun BAŞLADIĞI anı yakalar (fotoğraf çekmek için).

Durum sürdükçe tekrar tetiklemez. Tespit titreşirse (güvensiz → güvenli →
güvensiz) fotoğraf yağmuru olmasın diye iki tetikleme arasında en az
`cooldown_seconds` beklenir.
"""
from __future__ import annotations

import time
from typing import Callable


class UnsafeSituationWatcher:
    def __init__(self, cooldown_seconds: float, clock: Callable[[], float] = time.monotonic) -> None:
        self._cooldown_seconds = cooldown_seconds
        self._clock = clock
        self._was_unsafe = False
        self._last_trigger = float("-inf")

    def update(self, unsafe: bool) -> bool:
        """Yeni bir güvensiz durum başladıysa (ve bekleme süresi dolduysa) True döner."""
        started = unsafe and not self._was_unsafe
        self._was_unsafe = unsafe
        if not started:
            return False
        now = self._clock()
        if now - self._last_trigger < self._cooldown_seconds:
            return False
        self._last_trigger = now
        return True
