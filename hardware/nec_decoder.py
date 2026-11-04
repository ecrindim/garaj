"""Ham IR darbelerinden NEC kumanda kodlarını çözer.

NEC çerçevesi: ~9000 µs başlangıç darbesi + ~4500 µs boşluk, ardından 32 bit
(adres, ters adres, komut, ters komut; her bayt LSB önce). Her bit ~560 µs
darbe + kısa (0) ya da uzun (1) boşluktur. Tuş basılı tutulunca ~9000 µs
darbe + ~2250 µs boşluktan oluşan tekrar çerçeveleri gelir; bunlar yok sayılır.

Ucuz alıcılar (KY-022) darbeleri uzatıp boşlukları kısaltır; örneğin
başlangıç darbesi 10.400 µs ölçülebilir. Linux çekirdeğinin NEC çözücüsü
bunu reddettiği için toleranslı aralıklarla burada çözülür.
"""
from __future__ import annotations

from enum import Enum, auto
from typing import Optional

HEADER_PULSE_US = (7000, 12500)
HEADER_SPACE_US = (3500, 5500)
REPEAT_SPACE_US = (1700, 2900)
BIT_PULSE_US = (250, 1100)
ZERO_SPACE_US = (250, 1100)
ONE_SPACE_US = (1100, 2400)
FRAME_BITS = 32


def _within(value: int, limits: tuple[int, int]) -> bool:
    return limits[0] <= value <= limits[1]


class _Stage(Enum):
    IDLE = auto()
    HEADER_SPACE = auto()
    BIT_PULSE = auto()
    BIT_SPACE = auto()


class NecDecoder:
    def __init__(self) -> None:
        self._stage = _Stage.IDLE
        self._bits: list[int] = []

    def reset(self) -> None:
        self._stage = _Stage.IDLE
        self._bits = []

    def feed(self, is_pulse: bool, duration_us: int) -> Optional[int]:
        """Bir darbe/boşluk ver; tam ve geçerli bir çerçeve bittiyse kodu döner."""
        if self._stage is _Stage.IDLE:
            self._expect_header(is_pulse, duration_us)
        elif self._stage is _Stage.HEADER_SPACE:
            self._expect_header_space(is_pulse, duration_us)
        elif self._stage is _Stage.BIT_PULSE:
            self._expect_bit_pulse(is_pulse, duration_us)
        else:
            return self._expect_bit_space(is_pulse, duration_us)
        return None

    def _expect_header(self, is_pulse: bool, duration_us: int) -> None:
        self.reset()
        if is_pulse and _within(duration_us, HEADER_PULSE_US):
            self._stage = _Stage.HEADER_SPACE

    def _expect_header_space(self, is_pulse: bool, duration_us: int) -> None:
        if not is_pulse and _within(duration_us, HEADER_SPACE_US):
            self._stage = _Stage.BIT_PULSE
        else:
            self._expect_header(is_pulse, duration_us)  # Tekrar çerçevesi ya da gürültü

    def _expect_bit_pulse(self, is_pulse: bool, duration_us: int) -> None:
        if is_pulse and _within(duration_us, BIT_PULSE_US):
            self._stage = _Stage.BIT_SPACE
        else:
            self._expect_header(is_pulse, duration_us)

    def _expect_bit_space(self, is_pulse: bool, duration_us: int) -> Optional[int]:
        if is_pulse:
            self._expect_header(is_pulse, duration_us)
            return None
        if _within(duration_us, ZERO_SPACE_US):
            self._bits.append(0)
        elif _within(duration_us, ONE_SPACE_US):
            self._bits.append(1)
        else:
            self.reset()
            return None

        if len(self._bits) < FRAME_BITS:
            self._stage = _Stage.BIT_PULSE
            return None
        code = _frame_to_scancode(self._bits)
        self.reset()
        return code


def _frame_to_scancode(bits: list[int]) -> Optional[int]:
    address, address_inv, command, command_inv = (
        sum(bit << i for i, bit in enumerate(bits[start:start + 8])) for start in (0, 8, 16, 24)
    )
    if command ^ command_inv != 0xFF:
        return None  # Bozuk çerçeve
    if address ^ address_inv == 0xFF:
        return (address << 8) | command  # Standart NEC (Linux ile aynı kodlama)
    return (address << 16) | (address_inv << 8) | command  # Genişletilmiş NEC
