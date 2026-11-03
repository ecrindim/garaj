"""Kamera önizlemesine güvenli bölgeyi ve tespit kutularını çizer."""
from __future__ import annotations

from typing import Optional

import cv2
from picamera2 import MappedArray

from application.ports import StatusSnapshot
from domain.detection import ObjectCategory
from domain.geometry import BoundingBox

# Renkler BGRA (kamera XRGB8888 formatında çalışıyor)
GREEN = (0, 200, 0, 255)
RED = (0, 0, 230, 255)
ORANGE = (0, 140, 255, 255)
GRAY = (160, 160, 160, 255)
WHITE = (255, 255, 255, 255)

CATEGORY_COLORS = {
    ObjectCategory.VEHICLE: ORANGE,
    ObjectCategory.PERSON: RED,
    ObjectCategory.OTHER: GRAY,
}


class PreviewOverlay:
    def __init__(self, safe_zone: BoundingBox) -> None:
        self._safe_zone = safe_zone
        self._snapshot: Optional[StatusSnapshot] = None

    def update(self, snapshot: StatusSnapshot) -> None:
        self._snapshot = snapshot

    def draw(self, request) -> None:
        """Picamera2 pre_callback olarak her karede çağrılır."""
        snapshot = self._snapshot
        with MappedArray(request, "main") as mapped:
            frame = mapped.array
            is_safe = snapshot is not None and snapshot.safety.is_safe
            self._draw_box(frame, self._safe_zone, GREEN if is_safe else RED, "GUVENLI BOLGE", 3)
            if snapshot is None:
                return
            for detection in snapshot.detections:
                label = f"{detection.label} {detection.confidence:.0%}"
                self._draw_box(frame, detection.box, CATEGORY_COLORS[detection.category], label, 2)
            cv2.putText(frame, f"Motor: {snapshot.state.name}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, WHITE, 2)

    @staticmethod
    def _draw_box(frame, box: BoundingBox, color, text: str, thickness: int) -> None:
        height, width = frame.shape[:2]
        top_left = (int(box.x1 * width), int(box.y1 * height))
        bottom_right = (int(box.x2 * width), int(box.y2 * height))
        cv2.rectangle(frame, top_left, bottom_right, color, thickness)
        cv2.putText(frame, text, (top_left[0] + 4, top_left[1] + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
