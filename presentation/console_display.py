"""Durumu terminale yazar.

Durum değiştiğinde hemen, değişmese bile `refresh_seconds` aralıklarla
(FPS'i görebilmek için) yeni satır basar.
"""
from __future__ import annotations

import math
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
        text = (
            f"Düğme: {button:<9} | Motor: {snapshot.state.value:<14} | "
            f"Konum: {snapshot.position.value:<6} | Komut: {snapshot.command.value:<6} | "
            f"Araç: {vehicle:<14} | Canlı: {living:<3} | {snapshot.safety.status.value}"
        )
        if snapshot.seconds_until_home is not None:
            text += f" | Home'a: {math.ceil(snapshot.seconds_until_home)} sn"
        return text
