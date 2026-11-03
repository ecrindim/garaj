"""Döndürmenin güvenli olup olmadığına karar veren iş kuralları.

Kurallar:
  1. Platformun çevresinde (araç içi hariç) canlı (insan, kedi, köpek) varsa döndürme yok.
  2. Bir araç güvenli bölgeyle çakışıyor ama tamamen içinde değilse döndürme yok.
  3. Güvenli bölgenin tamamen içinde en az bir araç yoksa döndürme yok.

Araç içindeki canlıları ayırt edemediğimiz için, merkezi bir aracın
kutusu içinde kalan canlı tespitleri yok sayılır.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from domain.detection import Detection
from domain.zones import ZoneProvider


class SafetyStatus(Enum):
    SAFE = "Güvenli, döndürülebilir"
    LIVING_NEARBY = "Platform çevresinde canlı var"
    VEHICLE_CROSSING_BOUNDARY = "Araç güvenli bölge sınırını aşıyor"
    NO_VEHICLE_ON_PLATFORM = "Güvenli bölgede araç yok"


@dataclass(frozen=True)
class SafetyReport:
    status: SafetyStatus
    vehicle_on_platform: bool
    vehicle_crossing: bool
    living_nearby: bool

    @property
    def is_safe(self) -> bool:
        return self.status is SafetyStatus.SAFE

    @property
    def vehicle_secure(self) -> bool:
        """Araç bölgenin içinde ve hiçbir araç sınırı aşmıyor."""
        return self.vehicle_on_platform and not self.vehicle_crossing


class SafetyChecker:
    def __init__(self, zone_provider: ZoneProvider) -> None:
        self._zone_provider = zone_provider

    def evaluate(self, detections: Sequence[Detection]) -> SafetyReport:
        zone = self._zone_provider.current_zone()
        vehicles = [d for d in detections if d.is_vehicle]
        living_nearby = self.is_living_nearby(detections)
        vehicle_on_platform = any(zone.contains_box(v.box) for v in vehicles)
        vehicle_crossing = any(
            zone.intersects_box(v.box) and not zone.contains_box(v.box) for v in vehicles
        )

        status = self._decide_status(living_nearby, vehicle_crossing, vehicle_on_platform)
        return SafetyReport(status, vehicle_on_platform, vehicle_crossing, living_nearby)

    def is_living_nearby(self, detections: Sequence[Detection]) -> bool:
        vehicles = [d for d in detections if d.is_vehicle]
        living = [d for d in detections if d.is_living]
        return any(not self._is_inside_any_vehicle(l, vehicles) for l in living)

    @staticmethod
    def _decide_status(living_nearby: bool, vehicle_crossing: bool, vehicle_on_platform: bool) -> SafetyStatus:
        if living_nearby:
            return SafetyStatus.LIVING_NEARBY
        if vehicle_crossing:
            return SafetyStatus.VEHICLE_CROSSING_BOUNDARY
        if not vehicle_on_platform:
            return SafetyStatus.NO_VEHICLE_ON_PLATFORM
        return SafetyStatus.SAFE

    @staticmethod
    def _is_inside_any_vehicle(living: Detection, vehicles: Sequence[Detection]) -> bool:
        return any(v.box.contains_point(living.box.center) for v in vehicles)
