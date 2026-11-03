"""Aynı durumu birden fazla ekrana (konsol, önizleme...) iletir."""
from __future__ import annotations

from typing import Sequence

from application.ports import StatusDisplay, StatusSnapshot


class CompositeDisplay:
    def __init__(self, displays: Sequence[StatusDisplay]) -> None:
        self._displays = list(displays)

    def update(self, snapshot: StatusSnapshot) -> None:
        for display in self._displays:
            display.update(snapshot)
