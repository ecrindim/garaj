"""Kırmızı LED, beyaz LED ve buzzer ile durum gösterimi."""
from __future__ import annotations

import logging

from config import GpioConfig

logger = logging.getLogger(__name__)


class GpioStatusIndicator:
    """Duruyorken kırmızı LED; dönerken beyaz LED + kesikli buzzer."""

    def __init__(self, config: GpioConfig) -> None:
        from gpiozero import LED, Buzzer  # Pi dışında import hatası vermesin diye burada

        self._config = config
        self._red_led = LED(config.red_led_pin)
        self._white_led = LED(config.white_led_pin)
        self._buzzer = Buzzer(config.buzzer_pin)

    def show_idle(self) -> None:
        self._buzzer.off()
        self._white_led.off()
        self._red_led.on()

    def show_rotating(self) -> None:
        self._red_led.off()
        self._white_led.on()
        self._buzzer.beep(
            on_time=self._config.buzzer_on_seconds,
            off_time=self._config.buzzer_off_seconds,
        )

    def close(self) -> None:
        for device in (self._buzzer, self._white_led, self._red_led):
            device.off()
            device.close()


class ConsoleStatusIndicator:
    """GPIO kullanılamadığında aynı durumları ekrana yazar."""

    def show_idle(self) -> None:
        logger.info("[GÖSTERGE] Kırmızı LED AÇIK | Beyaz LED kapalı | Buzzer sessiz")

    def show_rotating(self) -> None:
        logger.info("[GÖSTERGE] Kırmızı LED kapalı | Beyaz LED AÇIK | Buzzer ÖTÜYOR")

    def close(self) -> None:
        pass
