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
from domain.geometry import BoundingBox


class SafetyStatus(Enum):
    SAFE = "Güvenli, döndürülebilir"
    LIVING_NEARBY = "Platform çevresinde canlı var"
    VEHICLE_CROSSING_BOUNDARY = "Araç güvenli bölge sınırını aşıyor"
    NO_VEHICLE_ON_PLATFORM = "Güvenli bölgede araç yok"


@dataclass(frozen=True)
class SafetyReport:
    status: SafetyStatus
    vehicle_on_platform: bool
    living_nearby: bool

    @property
    def is_safe(self) -> bool:
        return self.status is SafetyStatus.SAFE


class SafetyChecker:
    def __init__(self, safe_zone: BoundingBox) -> None:
        self._safe_zone = safe_zone

    @property
    def safe_zone(self) -> BoundingBox:
        return self._safe_zone

    def evaluate(self, detections: Sequence[Detection]) -> SafetyReport:
        vehicles = [d for d in detections if d.is_vehicle]
        living_nearby = self.is_living_nearby(detections)
        vehicle_on_platform = any(self._is_fully_inside(v) for v in vehicles)
        vehicle_crossing = any(self._is_crossing_boundary(v) for v in vehicles)

        status = self._decide_status(living_nearby, vehicle_crossing, vehicle_on_platform)
        return SafetyReport(status, vehicle_on_platform, living_nearby)

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

    def _is_fully_inside(self, vehicle: Detection) -> bool:
        return self._safe_zone.contains_box(vehicle.box)

    def _is_crossing_boundary(self, vehicle: Detection) -> bool:
        return self._safe_zone.intersects(vehicle.box) and not self._is_fully_inside(vehicle)

    @staticmethod
    def _is_inside_any_vehicle(living: Detection, vehicles: Sequence[Detection]) -> bool:
        return any(v.box.contains_point(living.box.center) for v in vehicles)
