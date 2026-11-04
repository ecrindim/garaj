"""Basılma olayını bir kez okunacak şekilde saklayan düğme.

Klavye ve IR kumanda dinleyicileri tuşa basıldığında `press()` çağırır;
kontrolcü `was_pressed()` ile olayı okur ve tüketir. Aynı düğmeye birden
fazla kaynak (klavye + kumanda) bağlanabilir.
"""
from __future__ import annotations

import threading


class EventButton:
    def __init__(self) -> None:
        self._pressed = threading.Event()

    def press(self) -> None:
        self._pressed.set()

    def was_pressed(self) -> bool:
        if self._pressed.is_set():
            self._pressed.clear()
            return True
        return False
