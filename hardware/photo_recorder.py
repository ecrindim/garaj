"""Olay fotoğraflarını tarih klasörlerine kaydeder ve eskilerini siler.

Yapı: photos/2026-11-04/14-32-05-123_dondurme_onaylandi.jpg
"""
from __future__ import annotations

import logging
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable

from application.ports import PhotoEvent, SnapshotCamera

logger = logging.getLogger(__name__)

DATE_FOLDER_FORMAT = "%Y-%m-%d"


class FilePhotoRecorder:
    def __init__(
        self,
        camera: SnapshotCamera,
        directory: str,
        retention_days: int,
        now: Callable[[], datetime] = datetime.now,
    ) -> None:
        self._camera = camera
        self._directory = Path(directory)
        self._retention_days = retention_days
        self._now = now

    def capture(self, event: PhotoEvent) -> None:
        timestamp = self._now()
        folder = self._directory / timestamp.strftime(DATE_FOLDER_FORMAT)
        folder.mkdir(parents=True, exist_ok=True)
        millis = timestamp.microsecond // 1000
        path = folder / f"{timestamp:%H-%M-%S}-{millis:03d}_{event.value}.jpg"
        try:
            self._camera.save_snapshot(str(path))
            logger.info("Fotoğraf kaydedildi: %s", path)
        except Exception:  # Fotoğraf hatası platform kontrolünü durdurmasın
            logger.exception("Fotoğraf kaydedilemedi: %s", path)

    def delete_expired(self) -> None:
        """Saklama süresini aşan tarih klasörlerini siler."""
        if not self._directory.exists():
            return
        oldest_kept = self._now().date() - timedelta(days=self._retention_days)
        for folder in self._directory.iterdir():
            folder_date = _parse_date(folder.name)
            if folder.is_dir() and folder_date is not None and folder_date < oldest_kept:
                shutil.rmtree(folder)
                logger.info("Eski fotoğraflar silindi: %s", folder)


def _parse_date(name: str):
    try:
        return datetime.strptime(name, DATE_FOLDER_FORMAT).date()
    except ValueError:
        return None
