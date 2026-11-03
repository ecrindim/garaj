"""Durumu terminale yazar.

Durum değiştiğinde hemen, değişmese bile `refresh_seconds` aralıklarla
(FPS'i görebilmek için) yeni satır basar.
"""
from __future__ import annotations

import time
from typing import Callable, Optional

from application.ports import StatusSnapshot


class ConsoleDisplay:
    def __init__(self, refresh_seconds: float = 2.0, clock: Callable[[], float] = time.monotonic) -> None:
        self._refresh_seconds = refresh_seconds
        self._clock = clock
        self._last_state_text: Optional[str] = None
        self._last_print_time = float("-inf")

    def update(self, snapshot: StatusSnapshot) -> None:
        state_text = self._format_state(snapshot)
        now = self._clock()
        changed = state_text != self._last_state_text
        if changed or now - self._last_print_time >= self._refresh_seconds:
            print(f"FPS: {snapshot.fps:4.1f} | {state_text}", flush=True)
            self._last_state_text = state_text
            self._last_print_time = now

    @staticmethod
    def _format_state(snapshot: StatusSnapshot) -> str:
        button = "BASILDI" if snapshot.button_pressed else "basılmadı"
        vehicle = "platformda" if snapshot.safety.vehicle_secure else "yok/sınır dışı"
        living = "VAR" if snapshot.safety.living_nearby else "yok"
        return (
            f"Düğme: {button:<9} | Motor: {snapshot.state.value:<7} | "
            f"Komut: {snapshot.rotate_command} | Araç: {vehicle:<14} | "
            f"Canlı: {living:<3} | {snapshot.safety.status.value}"
        )
