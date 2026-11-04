"""Kamera önizlemesine yuvarlak güvenli bölgeyi, tespitleri ve FPS'i çizer."""
from __future__ import annotations

import math
from typing import Optional

import cv2
from picamera2 import MappedArray

from application.ports import StatusSnapshot
from application.zone_store import ZoneStore
from domain.detection import ObjectCategory
from domain.geometry import BoundingBox

# Renkler BGRA (kamera XRGB8888 formatında çalışıyor)
GREEN = (0, 200, 0, 255)
RED = (0, 0, 230, 255)
ORANGE = (0, 140, 255, 255)
WHITE = (255, 255, 255, 255)

CATEGORY_COLORS = {
    ObjectCategory.VEHICLE: ORANGE,
    ObjectCategory.LIVING: RED,
}
FONT = cv2.FONT_HERSHEY_SIMPLEX


class PreviewOverlay:
    def __init__(self, zone_store: ZoneStore) -> None:
        self._zone_store = zone_store
        self._snapshot: Optional[StatusSnapshot] = None

    def update(self, snapshot: StatusSnapshot) -> None:
        self._snapshot = snapshot

    def draw(self, request) -> None:
        """Picamera2 pre_callback olarak her karede çağrılır."""
        snapshot = self._snapshot
        with MappedArray(request, "main") as mapped:
            frame = mapped.array
            is_safe = snapshot is not None and snapshot.safety.is_safe
            self._draw_zone(frame, GREEN if is_safe else RED)
            if snapshot is None:
                return
            for detection in snapshot.detections:
                label = f"{detection.label} {detection.confidence:.0%}"
                self._draw_box(frame, detection.box, CATEGORY_COLORS[detection.category], label)
            self._draw_status(frame, snapshot)

    def _draw_zone(self, frame, color) -> None:
        zone = self._zone_store.current_zone()
        height, width = frame.shape[:2]
        center = (int(zone.center.x * width), int(zone.center.y * height))
        radius = int(zone.radius * height)
        cv2.circle(frame, center, radius, color, 3)

    @staticmethod
    def _draw_box(frame, box: BoundingBox, color, text: str) -> None:
        height, width = frame.shape[:2]
        top_left = (int(box.x1 * width), int(box.y1 * height))
        bottom_right = (int(box.x2 * width), int(box.y2 * height))
        cv2.rectangle(frame, top_left, bottom_right, color, 2)
        cv2.putText(frame, text, (top_left[0] + 4, top_left[1] + 20), FONT, 0.6, color, 2)

    @staticmethod
    def _draw_status(frame, snapshot: StatusSnapshot) -> None:
        # OpenCV Türkçe karakter çizemediği için enum adları (ASCII) kullanılır
        lines = [
            f"FPS: {snapshot.fps:.1f}",
            f"Motor: {snapshot.state.name}",
            f"Konum: {snapshot.position.name}",
        ]
        if snapshot.seconds_until_home is not None:
            lines.append(f"HOME: {math.ceil(snapshot.seconds_until_home)} sn")
        for index, line in enumerate(lines):
            cv2.putText(frame, line, (10, 30 + index * 30), FONT, 0.8, WHITE, 2)
