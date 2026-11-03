"""Gerçek motor gelene kadar dönüşü süreye bağlı olarak simüle eder."""
from __future__ import annotations

import logging
import time
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class SimulatedMotor:
    def __init__(self, rotation_seconds: float, clock: Callable[[], float] = time.monotonic) -> None:
        self._rotation_seconds = rotation_seconds
        self._clock = clock
        self._started_at: Optional[float] = None

    def start_rotation(self) -> None:
        self._started_at = self._clock()
        logger.info(">>> MOTOR DÖNÜYOR (simülasyon, %.1f sn)", self._rotation_seconds)

    def stop(self) -> None:
        self._started_at = None
        logger.info(">>> MOTOR DURDU")

    def is_rotation_complete(self) -> bool:
        if self._started_at is None:
            return False
        return self._clock() - self._started_at >= self._rotation_seconds
