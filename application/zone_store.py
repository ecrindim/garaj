"""Çalışırken ayarlanabilen yuvarlak güvenli bölge.

Klavyeden büyütme/küçültme/taşıma komutları buraya gelir; SafetyChecker
ve önizleme her karede güncel bölgeyi buradan okur.
"""
from __future__ import annotations

import logging
import threading

from application.ports import ZoneRepository
from domain.geometry import Point
from domain.zones import CircularZone

logger = logging.getLogger(__name__)

MIN_RADIUS = 0.05
MAX_RADIUS = 1.0


class ZoneStore:
    def __init__(self, zone: CircularZone, repository: ZoneRepository) -> None:
        self._zone = zone
        self._repository = repository
        self._lock = threading.Lock()

    def current_zone(self) -> CircularZone:
        with self._lock:
            return self._zone

    def resize(self, delta: float) -> None:
        with self._lock:
            radius = _clamp(self._zone.radius + delta, MIN_RADIUS, MAX_RADIUS)
            self._zone = self._zone.with_radius(radius)
        self._log_zone("Bölge boyutu değişti")

    def move(self, dx: float, dy: float) -> None:
        with self._lock:
            center = Point(
                _clamp(self._zone.center.x + dx, 0.0, 1.0),
                _clamp(self._zone.center.y + dy, 0.0, 1.0),
            )
            self._zone = self._zone.with_center(center)
        self._log_zone("Bölge taşındı")

    def save(self) -> None:
        zone = self.current_zone()
        self._repository.save(zone)
        self._log_zone("Bölge kaydedildi")

    def _log_zone(self, message: str) -> None:
        zone = self.current_zone()
        logger.info("%s → merkez=(%.2f, %.2f) yarıçap=%.2f",
                    message, zone.center.x, zone.center.y, zone.radius)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(value, high))
