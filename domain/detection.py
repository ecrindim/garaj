"""Kameradan gelen nesne tespitlerinin donanımdan bağımsız temsili."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from domain.geometry import BoundingBox


class ObjectCategory(Enum):
    VEHICLE = "araç"
    PERSON = "insan"
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
    def is_person(self) -> bool:
        return self.category is ObjectCategory.PERSON


class LabelClassifier:
    """Modelin ham etiketini (car, truck, person...) kategoriye çevirir."""

    def __init__(self, vehicle_labels: frozenset[str], person_labels: frozenset[str]) -> None:
        self._vehicle_labels = vehicle_labels
        self._person_labels = person_labels

    def categorize(self, label: str) -> ObjectCategory:
        if label in self._vehicle_labels:
            return ObjectCategory.VEHICLE
        if label in self._person_labels:
            return ObjectCategory.PERSON
        return ObjectCategory.OTHER
