"""Terminalden tuşları anında (Enter'sız) okuyup bağlı komutları çalıştırır.

Ok tuşları "UP", "DOWN", "LEFT", "RIGHT" adlarıyla bağlanır. Terminale
göre ok tuşları "ESC [ A", "ESC O A" ya da "ESC [ 1 ; 2 A" gibi farklı
kodlar gönderebilir; hepsinin son harfine bakılarak çözümlenir.
Bağlı olmayan bir tuşa basılınca ne geldiği loglanır (tanı için).
"""
from __future__ import annotations

import logging
import os
import select
import sys
import termios
import threading
import tty
from typing import Callable, Mapping

logger = logging.getLogger(__name__)

POLL_SECONDS = 0.1
ESCAPE_TIMEOUT_SECONDS = 0.05
MAX_ESCAPE_LENGTH = 8
ARROW_FINAL_CHARS = {"A": "UP", "B": "DOWN", "C": "RIGHT", "D": "LEFT"}

KeyBindings = Mapping[str, Callable[[], None]]


class KeyboardListener:
    def __init__(self, bindings: KeyBindings) -> None:
        self._bindings = dict(bindings)
        self._stopped = threading.Event()
        self._fd = sys.stdin.fileno()
        self._original_settings = termios.tcgetattr(self._fd)
        tty.setcbreak(self._fd)
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()

    def close(self) -> None:
        self._stopped.set()
        termios.tcsetattr(self._fd, termios.TCSADRAIN, self._original_settings)

    def _listen(self) -> None:
        while not self._stopped.is_set():
            char = self._read_char(POLL_SECONDS)
            if char:
                self._dispatch(self._resolve_key(char))

    def _resolve_key(self, char: str) -> str:
        if char != "\x1b":
            return char.lower()
        return self._resolve_escape_sequence(self._read_escape_sequence())

    def _read_escape_sequence(self) -> str:
        introducer = self._read_char(ESCAPE_TIMEOUT_SECONDS)
        if introducer == "O":  # "ESC O A" biçimi: tek karakter daha gelir
            return introducer + self._read_char(ESCAPE_TIMEOUT_SECONDS)
        if introducer != "[":
            return introducer

        sequence = introducer  # "ESC [ ... A" biçimi: harf ya da ~ gelene kadar oku
        while len(sequence) < MAX_ESCAPE_LENGTH:
            char = self._read_char(ESCAPE_TIMEOUT_SECONDS)
            if not char:
                break
            sequence += char
            if char.isalpha() or char == "~":
                break
        return sequence

    @staticmethod
    def _resolve_escape_sequence(sequence: str) -> str:
        if len(sequence) >= 2 and sequence[0] in "[O":
            arrow = ARROW_FINAL_CHARS.get(sequence[-1])
            if arrow:
                return arrow
        return "ESC" + sequence

    def _read_char(self, timeout: float) -> str:
        ready, _, _ = select.select([self._fd], [], [], timeout)
        return os.read(self._fd, 1).decode(errors="ignore") if ready else ""

    def _dispatch(self, key: str) -> None:
        action = self._bindings.get(key)
        if action is None:
            logger.info("Tanımsız tuş geldi: %r", key)
            return
        try:
            action()
        except Exception:  # Bir tuşun hatası dinleyiciyi öldürmesin
            logger.exception("'%s' tuşunun komutu çalıştırılamadı", key)
