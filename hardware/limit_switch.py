"""Mekanik limit switch okuma (home ve 90° switch'leri için).

Bağlantı: switch'in NO (normalde açık) kontağının bir ucu GPIO pinine, diğer
ucu GND'ye. Pi'nin dahili pull-up direnci açılır; platform switch'e
bastığında pin LOW olur ve `is_triggered()` True döner.

Switch Pi'nin 3.3V'u ile çalışır; ayrı bir besleme ya da gerilim bölücü
gerekmez. Panodaki (yüksek voltajlı) devreye bağlı bir kontak KULLANILMAZ.
"""
from __future__ import annotations


class LimitSwitch:
    def __init__(self, pin: int) -> None:
        from gpiozero import DigitalInputDevice  # Pi dışında import hatası vermesin

        self._device = DigitalInputDevice(pin, pull_up=True)

    def is_triggered(self) -> bool:
        return self._device.is_active

    def close(self) -> None:
        self._device.close()
