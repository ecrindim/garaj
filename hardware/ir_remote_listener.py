"""KY-022 IR alıcının ham sinyalini (/dev/lircN) okuyup kumanda tuşlarını çalıştırır.

Linux `gpio-ir` sürücüsü alıcıyı bir LIRC aygıtı olarak sunar. Ham darbe
süreleri buradan okunur ve `NecDecoder` ile çözülür (çekirdeğin kendi NEC
çözücüsü KY-022'nin uzattığı sinyalleri reddettiği için).

Bağlı olmayan bir kod gelirse loglanır (yeni tuş eşlemek için).
"""
from __future__ import annotations

import fcntl
import glob
import logging
import os
import select
import struct
import threading
import time
from pathlib import Path
from typing import Callable, Mapping, Optional

from hardware.nec_decoder import NecDecoder

logger = logging.getLogger(__name__)

POLL_SECONDS = 0.2
READ_BYTES = 4096
SAMPLE_BYTES = 4

# linux/lirc.h
LIRC_SET_REC_MODE = 0x40046912
LIRC_MODE_MODE2 = 0x00000004
LIRC_MODE2_MASK = 0xFF000000
LIRC_VALUE_MASK = 0x00FFFFFF
LIRC_MODE2_PULSE = 0x01000000
LIRC_MODE2_SPACE = 0x00000000
LIRC_MODE2_TIMEOUT = 0x03000000

IrBindings = Mapping[int, Callable[[], None]]


def find_lirc_device(driver_name: str) -> str:
    """Sürücü adına göre LIRC aygıtını bulur (rc numarası açılıştan açılışa değişebilir)."""
    for rc_dir in sorted(glob.glob("/sys/class/rc/rc*")):
        uevent = Path(rc_dir, "uevent")
        if not uevent.exists() or driver_name not in uevent.read_text(errors="ignore"):
            continue
        for lirc_dir in glob.glob(f"{rc_dir}/lirc*"):
            return f"/dev/{Path(lirc_dir).name}"
    raise RuntimeError(f"'{driver_name}' IR alıcısının LIRC aygıtı bulunamadı")


class IrRemoteListener:
    def __init__(
        self,
        driver_name: str,
        bindings: IrBindings,
        repeat_suppress_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._device_path = find_lirc_device(driver_name)
        self._fd = os.open(self._device_path, os.O_RDONLY | os.O_NONBLOCK)
        self._set_raw_mode()
        self._decoder = NecDecoder()
        self._bindings = dict(bindings)
        self._repeat_suppress_seconds = repeat_suppress_seconds
        self._clock = clock
        self._last_code: Optional[int] = None
        self._last_time = float("-inf")
        self._stopped = threading.Event()
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()
        logger.info("IR kumanda dinleniyor: %s", self._device_path)

    def close(self) -> None:
        self._stopped.set()
        self._thread.join(timeout=1)
        os.close(self._fd)

    def _set_raw_mode(self) -> None:
        try:
            fcntl.ioctl(self._fd, LIRC_SET_REC_MODE, struct.pack("I", LIRC_MODE_MODE2))
        except OSError as error:  # Zaten ham moddaysa sorun değil
            logger.debug("LIRC ham mod ayarlanamadı: %s", error)

    def _listen(self) -> None:
        buffer = b""
        while not self._stopped.is_set():
            ready, _, _ = select.select([self._fd], [], [], POLL_SECONDS)
            if not ready:
                continue
            try:
                buffer += os.read(self._fd, READ_BYTES)
            except BlockingIOError:
                continue
            usable = len(buffer) - len(buffer) % SAMPLE_BYTES
            for (sample,) in struct.iter_unpack("I", buffer[:usable]):
                self._handle_sample(sample)
            buffer = buffer[usable:]

    def _handle_sample(self, sample: int) -> None:
        kind = sample & LIRC_MODE2_MASK
        duration = sample & LIRC_VALUE_MASK
        if kind == LIRC_MODE2_TIMEOUT:
            self._decoder.reset()
            return
        if kind not in (LIRC_MODE2_PULSE, LIRC_MODE2_SPACE):
            return
        code = self._decoder.feed(kind == LIRC_MODE2_PULSE, duration)
        if code is not None:
            self._handle_code(code)

    def _handle_code(self, code: int) -> None:
        if self._is_repeat(code):
            return
        action = self._bindings.get(code)
        if action is None:
            logger.info("Tanımsız IR kodu geldi: 0x%X", code)
            return
        try:
            action()
        except Exception:  # Bir tuşun hatası dinleyiciyi öldürmesin
            logger.exception("IR kodu 0x%X için komut çalıştırılamadı", code)

    def _is_repeat(self, code: int) -> bool:
        now = self._clock()
        repeated = code == self._last_code and now - self._last_time < self._repeat_suppress_seconds
        self._last_code = code
        self._last_time = now
        return repeated
