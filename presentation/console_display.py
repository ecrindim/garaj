"""Durumu terminale yazar; sadece değişiklik olduğunda yeni satır basar."""
from __future__ import annotations

from typing import Optional

from application.ports import StatusSnapshot


class ConsoleDisplay:
    def __init__(self) -> None:
        self._last_line: Optional[str] = None

    def update(self, snapshot: StatusSnapshot) -> None:
        line = self._format(snapshot)
        if line != self._last_line:
            print(line, flush=True)
            self._last_line = line

    @staticmethod
    def _format(snapshot: StatusSnapshot) -> str:
        button = "BASILDI" if snapshot.button_pressed else "basılmadı"
        vehicle = "platformda" if snapshot.safety.vehicle_on_platform else "yok/sınır dışı"
        person = "VAR" if snapshot.safety.person_nearby else "yok"
        return (
            f"Düğme: {button:<9} | Motor: {snapshot.state.value:<7} | "
            f"Komut: {snapshot.rotate_command} | Araç: {vehicle:<14} | "
            f"İnsan: {person:<3} | {snapshot.safety.status.value}"
        )
