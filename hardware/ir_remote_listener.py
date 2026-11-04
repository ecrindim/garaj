"""KY-022 IR alıcıdan kumanda tuşlarını okuyup bağlı komutları çalıştırır.

Linux `gpio-ir` sürücüsü kumanda sinyalini çözer ve bir giriş aygıtı
(/dev/input/eventX) olarak sunar. Her tuş basışında NEC tarama kodu
(scancode) EV_MSC/MSC_SCAN olayı olarak gelir.

Tuş basılı tutulunca kumanda aynı kodu ~110 ms'de bir tekrarlar; bu
tekrarlar `repeat_suppress_seconds` boyunca yok sayılır. Bağlı olmayan
bir kod gelirse loglanır (yeni tuş eşlemek için).
"""
from __future__ import annotations

import logging
import select
import threading
import time
from typing import Callable, Mapping, Optional

logger = logging.getLogger(__name__)

POLL_SECONDS = 0.2
IrBindings = Mapping[int, Callable[[], None]]


class IrRemoteListener:
    def __init__(
        self,
        device_name: str,
        bindings: IrBindings,
        repeat_suppress_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        from evdev import InputDevice, ecodes, list_devices  # Pi dışında import hatası vermesin

        self._ecodes = ecodes
        self._device = self._find_device(device_name, InputDevice, list_devices)
        self._bindings = dict(bindings)
        self._repeat_suppress_seconds = repeat_suppress_seconds
        self._clock = clock
        self._last_code: Optional[int] = None
        self._last_time = float("-inf")
        self._stopped = threading.Event()
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()
        logger.info("IR kumanda dinleniyor: %s (%s)", self._device.name, self._device.path)

    def close(self) -> None:
        self._stopped.set()
        self._thread.join(timeout=1)
        self._device.close()

    @staticmethod
    def _find_device(device_name: str, input_device_type, list_devices):
        for path in list_devices():
            device = input_device_type(path)
            if device_name in device.name:
                return device
            device.close()
        raise RuntimeError(f"'{device_name}' adlı IR alıcı aygıtı bulunamadı")

    def _listen(self) -> None:
        while not self._stopped.is_set():
            ready, _, _ = select.select([self._device.fd], [], [], POLL_SECONDS)
            if not ready:
                continue
            for event in self._device.read():
                if event.type == self._ecodes.EV_MSC and event.code == self._ecodes.MSC_SCAN:
                    self._handle_code(event.value)

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
        self._last_time = now  # Basılı tutuldukça bastırma süresi uzar
        return repeated
