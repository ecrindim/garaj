"""E18-D80NK kızılötesi yakınlık sensörü ile 90° konumunu algılar.

Sensör NPN çıkışlıdır: önünde cisim (metal) varken çıkışı LOW'a çeker.
Pi'nin dahili pull-up direnci açılır; gpiozero'da `pull_up=True` ile
pin LOW olduğunda `is_active` True döner.
"""
from __future__ import annotations


class ProximityPositionSensor:
    def __init__(self, pin: int) -> None:
        from gpiozero import DigitalInputDevice  # Pi dışında import hatası vermesin

        self._device = DigitalInputDevice(pin, pull_up=True)

    def is_triggered(self) -> bool:
        return self._device.is_active

    def close(self) -> None:
        self._device.close()
