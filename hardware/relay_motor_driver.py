"""4 kanallı röle modülüyle (SRD-05VDC-SL-C) motor panosuna komut verir.

- Röle 1 kapalı → pano motoru saat yönünün tersine (90°'ye) döndürür.
- Röle 2 kapalı → pano motoru saat yönünde (home'a) döndürür.
- Röle açılınca motor durur (panoda mühürleme yok, "basılı tutma" mantığı).

Güvenlik:
- İki röle asla aynı anda kapalı olmaz.
- Yön değişiminde iki röle arasında `dead_time_seconds` beklenir.
- Modül aktif-LOW'dur: pin LOW → röle çeker. Varsayılan pinler GPIO2/GPIO3'te
  kart üzerinde sabit pull-up olduğundan Pi açılırken ya da program çalışmıyorken
  pinler HIGH kalır ve röleler bırakık durur.
"""
from __future__ import annotations

import logging
import time
from typing import Callable

logger = logging.getLogger(__name__)


class RelayMotorDriver:
    def __init__(
        self,
        rotate_pin: int,
        home_pin: int,
        active_low: bool,
        dead_time_seconds: float,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        from gpiozero import OutputDevice  # Pi dışında import hatası vermesin

        def relay(pin: int):
            return OutputDevice(pin, active_high=not active_low, initial_value=False)

        self._rotate_relay = relay(rotate_pin)
        self._home_relay = relay(home_pin)
        self._dead_time_seconds = dead_time_seconds
        self._clock = clock
        self._sleep = sleep
        self._last_released_at = float("-inf")

    def start_rotate_out(self) -> None:
        self._energize(self._rotate_relay, other=self._home_relay)
        logger.info(">>> RÖLE: DÖNDÜR çekti (saat yönünün tersine)")

    def start_return_home(self) -> None:
        self._energize(self._home_relay, other=self._rotate_relay)
        logger.info(">>> RÖLE: HOME çekti (saat yönünde)")

    def stop(self) -> None:
        if self._rotate_relay.value or self._home_relay.value:
            self._last_released_at = self._clock()
        self._rotate_relay.off()
        self._home_relay.off()
        logger.info(">>> RÖLE: ikisi de bırakıldı, motor durdu")

    def close(self) -> None:
        self._rotate_relay.off()
        self._home_relay.off()
        self._rotate_relay.close()
        self._home_relay.close()

    def _energize(self, target, other) -> None:
        if other.value:
            other.off()
            self._last_released_at = self._clock()
        if target.value:
            return
        remaining = self._dead_time_seconds - (self._clock() - self._last_released_at)
        if remaining > 0:
            self._sleep(remaining)  # Yön değişiminde kontaktörlerin bırakmasını bekle
        target.on()
