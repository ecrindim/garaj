"""Güvenli bölge şekilleri.

`SafeZone` arayüzünü uygulayan her şekil güvenlik kontrolünde kullanılabilir;
yeni bir şekil eklemek için SafetyChecker'a dokunmak gerekmez.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Protocol

from domain.geometry import BoundingBox, Point


class SafeZone(Protocol):
    def contains_box(self, box: BoundingBox) -> bool: ...
    def intersects_box(self, box: BoundingBox) -> bool: ...


class ZoneProvider(Protocol):
    """Güncel güvenli bölgeyi verir (bölge çalışırken değiştirilebilir)."""

    def current_zone(self) -> SafeZone: ...


@dataclass(frozen=True)
class CircularZone:
    """Normalize koordinatlarda daire şeklinde güvenli bölge.

    Yarıçap görüntü YÜKSEKLİĞİNE oranlıdır. Görüntü kare olmadığından x
    ekseni `aspect_ratio` (genişlik / yükseklik) ile ölçeklenir; böylece
    ekranda elips değil gerçek bir daire elde edilir.
    """

    center: Point
    radius: float
    aspect_ratio: float

    def __post_init__(self) -> None:
        if self.radius <= 0 or self.aspect_ratio <= 0:
            raise ValueError(f"Geçersiz daire bölge: {self}")

    def with_center(self, center: Point) -> CircularZone:
        return replace(self, center=center)

    def with_radius(self, radius: float) -> CircularZone:
        return replace(self, radius=radius)

    def contains_point(self, point: Point) -> bool:
        return self._distance_to_center(point) <= self.radius

    def contains_box(self, box: BoundingBox) -> bool:
        # Daire dışbükey olduğundan 4 köşe içerideyse kutunun tamamı içeridedir.
        return all(self.contains_point(corner) for corner in box.corners)

    def intersects_box(self, box: BoundingBox) -> bool:
        nearest = Point(
            _clamp(self.center.x, box.x1, box.x2),
            _clamp(self.center.y, box.y1, box.y2),
        )
        return self._distance_to_center(nearest) < self.radius

    def _distance_to_center(self, point: Point) -> float:
        dx = (point.x - self.center.x) * self.aspect_ratio
        dy = point.y - self.center.y
        return math.hypot(dx, dy)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(value, high))
