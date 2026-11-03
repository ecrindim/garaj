"""Güvenli bölge ayarını JSON dosyasında saklar; açılışta geri yükler."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from domain.geometry import Point
from domain.zones import CircularZone

logger = logging.getLogger(__name__)


class JsonZoneRepository:
    def __init__(self, path: str, aspect_ratio: float) -> None:
        self._path = Path(path)
        self._aspect_ratio = aspect_ratio

    def load(self) -> Optional[CircularZone]:
        if not self._path.exists():
            return None
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            return CircularZone(
                center=Point(float(data["center_x"]), float(data["center_y"])),
                radius=float(data["radius"]),
                aspect_ratio=self._aspect_ratio,
            )
        except (ValueError, KeyError, TypeError) as error:
            logger.warning("%s okunamadı (%s), varsayılan bölge kullanılacak.", self._path, error)
            return None

    def save(self, zone: CircularZone) -> None:
        data = {
            "center_x": round(zone.center.x, 4),
            "center_y": round(zone.center.y, 4),
            "radius": round(zone.radius, 4),
        }
        self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")
