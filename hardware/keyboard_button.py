"""Gerçek kumanda gelene kadar klavyeyi döndürme düğmesi olarak kullanır.

Enter'a basmaya gerek yoktur; tuş anında okunur (terminal cbreak modu).
"""
from __future__ import annotations

import os
import select
import sys
import termios
import threading
import tty

POLL_SECONDS = 0.1


class KeyboardButton:
    def __init__(self, rotate_key: str, quit_key: str) -> None:
        self._rotate_key = rotate_key.lower()
        self._quit_key = quit_key.lower()
        self._pressed = threading.Event()
        self._quit = threading.Event()
        self._fd = sys.stdin.fileno()
        self._original_settings = termios.tcgetattr(self._fd)
        tty.setcbreak(self._fd)
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()

    def was_pressed(self) -> bool:
        """Son kontrolden beri tuşa basıldıysa True döner ve olayı tüketir."""
        if self._pressed.is_set():
            self._pressed.clear()
            return True
        return False

    @property
    def quit_requested(self) -> bool:
        return self._quit.is_set()

    def close(self) -> None:
        self._quit.set()
        termios.tcsetattr(self._fd, termios.TCSADRAIN, self._original_settings)

    def _listen(self) -> None:
        while not self._quit.is_set():
            ready, _, _ = select.select([self._fd], [], [], POLL_SECONDS)
            if ready:
                self._handle_key(os.read(self._fd, 1).decode(errors="ignore").lower())

    def _handle_key(self, key: str) -> None:
        if key == self._rotate_key:
            self._pressed.set()
        elif key == self._quit_key:
            self._quit.set()
