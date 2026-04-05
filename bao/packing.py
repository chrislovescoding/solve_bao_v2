from __future__ import annotations

from dataclasses import dataclass
from math import comb

from .reference import GameState, Player, canonical_key

TOTAL_SEEDS = 64
PIT_COUNT = 32
BAR_COUNT = PIT_COUNT - 1
SLOT_COUNT = TOTAL_SEEDS + BAR_COUNT
STATE_KEY_BYTES = 16


@dataclass(frozen=True)
class PackedStateKey:
    value: int

    def __post_init__(self) -> None:
        if self.value < 0:
            raise ValueError("PackedStateKey values must be non-negative.")
        if self.value >= 1 << (STATE_KEY_BYTES * 8):
            raise ValueError("PackedStateKey does not fit in 16 bytes.")

    @property
    def bytes_be(self) -> bytes:
        return self.value.to_bytes(STATE_KEY_BYTES, "big", signed=False)

    @property
    def hex(self) -> str:
        return self.bytes_be.hex()

    @classmethod
    def from_bytes(cls, payload: bytes) -> "PackedStateKey":
        if len(payload) != STATE_KEY_BYTES:
            raise ValueError(f"PackedStateKey payload must be {STATE_KEY_BYTES} bytes.")
        return cls(int.from_bytes(payload, "big", signed=False))


def _validate_pits(pits: tuple[int, ...] | list[int]) -> tuple[int, ...]:
    normalized = tuple(int(value) for value in pits)
    if len(normalized) != PIT_COUNT:
        raise ValueError(f"Expected {PIT_COUNT} pits, got {len(normalized)}.")
    if any(value < 0 for value in normalized):
        raise ValueError("Pit counts must be non-negative.")
    if sum(normalized) != TOTAL_SEEDS:
        raise ValueError(f"Expected {TOTAL_SEEDS} seeds, got {sum(normalized)}.")
    return normalized


def _bars_for_pits(pits: tuple[int, ...]) -> tuple[int, ...]:
    bars: list[int] = []
    running = 0
    for index, count in enumerate(pits[:-1]):
        running += count
        bars.append(running + index)
    return tuple(bars)


def _pits_from_bars(bars: tuple[int, ...]) -> tuple[int, ...]:
    pits: list[int] = []
    previous = -1
    for bar in bars:
        pits.append(bar - previous - 1)
        previous = bar
    pits.append((SLOT_COUNT - 1) - previous)
    return tuple(pits)


def rank_pits(pits: tuple[int, ...] | list[int]) -> int:
    normalized = _validate_pits(pits)
    bars = _bars_for_pits(normalized)
    return sum(comb(bar, index + 1) for index, bar in enumerate(bars))


def unrank_pits(rank: int) -> tuple[int, ...]:
    if rank < 0:
        raise ValueError("Rank must be non-negative.")

    bars = [0] * BAR_COUNT
    remainder = rank
    upper = SLOT_COUNT - 1

    for size in range(BAR_COUNT, 0, -1):
        candidate = upper
        while comb(candidate, size) > remainder:
            candidate -= 1
        bars[size - 1] = candidate
        remainder -= comb(candidate, size)
        upper = candidate - 1

    pits = _pits_from_bars(tuple(bars))
    return _validate_pits(pits)


def pack_canonical_pits(pits: tuple[int, ...] | list[int]) -> PackedStateKey:
    return PackedStateKey(rank_pits(pits))


def pack_canonical_state(state: GameState) -> PackedStateKey:
    return pack_canonical_pits(canonical_key(state))


def unpack_canonical_pits(key: PackedStateKey | int) -> tuple[int, ...]:
    rank = key.value if isinstance(key, PackedStateKey) else int(key)
    return unrank_pits(rank)


def unpack_canonical_state(key: PackedStateKey | int) -> GameState:
    return GameState(unpack_canonical_pits(key), Player.SOUTH)


def canonical_state_key_hex(state: GameState) -> str:
    return pack_canonical_state(state).hex

