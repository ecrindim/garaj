"""Gerçek kumanda gelene kadar döndürme düğmesini simüle eder.

Klavye dinleyicisi tuşa basıldığında `press()` çağırır; kontrolcü
`was_pressed()` ile olayı okur ve tüketir.
"""
from __future__ import annotations

import threading


class SimulatedButton:
    def __init__(self) -> None:
        self._pressed = threading.Event()

    def press(self) -> None:
        self._pressed.set()

    def was_pressed(self) -> bool:
        if self._pressed.is_set():
            self._pressed.clear()
            return True
        return False
