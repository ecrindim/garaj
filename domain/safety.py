"""Döndürmenin güvenli olup olmadığına karar veren iş kuralları.

Kurallar:
  1. Platformun çevresinde (araç içi hariç) insan varsa döndürme yok.
  2. Bir araç güvenli bölgeyle çakışıyor ama tamamen içinde değilse döndürme yok.
  3. Güvenli bölgenin tamamen içinde en az bir araç yoksa döndürme yok.

Araç içindeki insanları ayırt edemediğimiz için, merkezi bir aracın
kutusu içinde kalan insan tespitleri yok sayılır.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from domain.detection import Detection
from domain.geometry import BoundingBox


class SafetyStatus(Enum):
    SAFE = "Güvenli, döndürülebilir"
    PERSON_NEARBY = "Platform çevresinde insan var"
    VEHICLE_CROSSING_BOUNDARY = "Araç güvenli bölge sınırını aşıyor"
    NO_VEHICLE_ON_PLATFORM = "Güvenli bölgede araç yok"


@dataclass(frozen=True)
class SafetyReport:
    status: SafetyStatus
    vehicle_on_platform: bool
    person_nearby: bool

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
        person_nearby = self.is_person_nearby(detections)
        vehicle_on_platform = any(self._is_fully_inside(v) for v in vehicles)
        vehicle_crossing = any(self._is_crossing_boundary(v) for v in vehicles)

        status = self._decide_status(person_nearby, vehicle_crossing, vehicle_on_platform)
        return SafetyReport(status, vehicle_on_platform, person_nearby)

    def is_person_nearby(self, detections: Sequence[Detection]) -> bool:
        vehicles = [d for d in detections if d.is_vehicle]
        persons = [d for d in detections if d.is_person]
        return any(not self._is_inside_any_vehicle(p, vehicles) for p in persons)

    @staticmethod
    def _decide_status(person_nearby: bool, vehicle_crossing: bool, vehicle_on_platform: bool) -> SafetyStatus:
        if person_nearby:
            return SafetyStatus.PERSON_NEARBY
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
    def _is_inside_any_vehicle(person: Detection, vehicles: Sequence[Detection]) -> bool:
        return any(v.box.contains_point(person.box.center) for v in vehicles)
