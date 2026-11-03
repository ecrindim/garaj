"""Kameradan gelen nesne tespitlerinin donanımdan bağımsız temsili."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from domain.geometry import BoundingBox


class ObjectCategory(Enum):
    VEHICLE = "araç"
    LIVING = "canlı"
    OTHER = "diğer"


@dataclass(frozen=True)
class Detection:
    label: str
    category: ObjectCategory
    confidence: float
    box: BoundingBox

    @property
    def is_vehicle(self) -> bool:
        return self.category is ObjectCategory.VEHICLE

    @property
    def is_living(self) -> bool:
        return self.category is ObjectCategory.LIVING


class LabelClassifier:
    """Modelin ham etiketini (car, person, cat, dog...) kategoriye çevirir."""

    def __init__(self, vehicle_labels: frozenset[str], living_labels: frozenset[str]) -> None:
        self._vehicle_labels = vehicle_labels
        self._living_labels = living_labels

    def categorize(self, label: str) -> ObjectCategory:
        if label in self._vehicle_labels:
            return ObjectCategory.VEHICLE
        if label in self._living_labels:
            return ObjectCategory.LIVING
        return ObjectCategory.OTHER
