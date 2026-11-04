"""Gerçek motor ve röleler gelene kadar motor komutlarını ekrana yazar."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class ConsoleMotorDriver:
    def start_rotate_out(self) -> None:
        logger.info(">>> MOTOR DÖNÜYOR → 90° saat yönünün tersine")

    def start_return_home(self) -> None:
        logger.info(">>> MOTOR HOME'A DÖNÜYOR → saat yönünde")

    def stop(self) -> None:
        logger.info(">>> MOTOR DURDU")
