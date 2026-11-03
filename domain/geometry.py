"""Normalize (0..1) görüntü koordinatlarında temel geometri tipleri."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Point:
    x: float
    y: float


@dataclass(frozen=True)
class BoundingBox:
    """Sol-üst (x1, y1) ve sağ-alt (x2, y2) köşeleriyle tanımlı dikdörtgen.

    Tüm değerler görüntü genişliği/yüksekliğine göre normalize edilmiştir,
    böylece kamera çözünürlüğü değişse de güvenli bölge aynı kalır.
    """

    x1: float
    y1: float
    x2: float
    y2: float

    def __post_init__(self) -> None:
        if self.x2 <= self.x1 or self.y2 <= self.y1:
            raise ValueError(f"Geçersiz bounding box: {self}")

    @classmethod
    def from_xywh(cls, x: float, y: float, width: float, height: float) -> BoundingBox:
        return cls(x, y, x + width, y + height)

    @property
    def center(self) -> Point:
        return Point((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)

    def contains_box(self, other: BoundingBox) -> bool:
        """`other` kutusu tamamen bu kutunun içinde mi?"""
        return (
            other.x1 >= self.x1
            and other.y1 >= self.y1
            and other.x2 <= self.x2
            and other.y2 <= self.y2
        )

    def contains_point(self, point: Point) -> bool:
        return self.x1 <= point.x <= self.x2 and self.y1 <= point.y <= self.y2

    def intersects(self, other: BoundingBox) -> bool:
        """İki kutunun ortak alanı var mı?"""
        return not (
            other.x2 <= self.x1
            or other.x1 >= self.x2
            or other.y2 <= self.y1
            or other.y1 >= self.y2
        )
