from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import struct

from .artifacts import RULESPEC_VERSION
from .native_shards import HEADER, NativeShardHeader, parse_native_header


SOLUTION_MAGIC = b"BAOSOLVE"
SOLUTION_RECORD = struct.Struct("<BBIBB")
UNKNOWN_DISTANCE = 0xFFFFFFFF
UNKNOWN_MOVE_CODE = 0xFF

_OUTCOME_TO_CODE = {
    None: 0,
    "win": 1,
    "loss": 2,
    "draw": 3,
}
_OUTCOME_BY_CODE = {value: key for key, value in _OUTCOME_TO_CODE.items()}


@dataclass(frozen=True)
class NativeSolutionRecord:
    local_id: int
    outcome: str | None
    best_move_code: int | None
    distance: int | None
    partial: bool
    terminal_seed: bool
    frontier_dependent: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "local_id": self.local_id,
            "outcome": self.outcome,
            "best_move_code": self.best_move_code,
            "distance": self.distance,
            "partial": self.partial,
            "terminal_seed": self.terminal_seed,
            "frontier_dependent": self.frontier_dependent,
        }


def _flags(record: NativeSolutionRecord) -> int:
    flags = 0
    if record.partial:
        flags |= 1 << 0
    if record.terminal_seed:
        flags |= 1 << 1
    if record.frontier_dependent:
        flags |= 1 << 2
    return flags


def _record_from_tuple(local_id: int, unpacked: tuple[int, int, int, int, int]) -> NativeSolutionRecord:
    outcome_code, best_move_raw, distance_raw, flags, _reserved = unpacked
    best_move_code = None if best_move_raw == UNKNOWN_MOVE_CODE else int(best_move_raw)
    distance = None if distance_raw == UNKNOWN_DISTANCE else int(distance_raw)
    return NativeSolutionRecord(
        local_id=local_id,
        outcome=_OUTCOME_BY_CODE.get(outcome_code),
        best_move_code=best_move_code,
        distance=distance,
        partial=bool(flags & (1 << 0)),
        terminal_seed=bool(flags & (1 << 1)),
        frontier_dependent=bool(flags & (1 << 2)),
    )


def write_solution_shard(
    path: str | Path,
    records: list[NativeSolutionRecord],
    *,
    depth: int,
    resolved_count: int,
    rulespec_version: str = RULESPEC_VERSION,
) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload_bytes = len(records) * SOLUTION_RECORD.size

    header = bytearray(HEADER.size)
    offset = 0
    header[offset : offset + 8] = SOLUTION_MAGIC
    offset += 8
    header[offset : offset + 2] = (1).to_bytes(2, "little")
    offset += 2
    header[offset : offset + 2] = HEADER.size.to_bytes(2, "little")
    offset += 2
    header[offset : offset + 2] = SOLUTION_RECORD.size.to_bytes(2, "little")
    offset += 2
    header[offset : offset + 2] = int(depth).to_bytes(2, "little")
    offset += 2
    header[offset : offset + 8] = len(records).to_bytes(8, "little")
    offset += 8
    header[offset : offset + 8] = payload_bytes.to_bytes(8, "little")
    offset += 8
    header[offset : offset + 8] = int(resolved_count).to_bytes(8, "little")
    offset += 8
    version_bytes = rulespec_version.encode("ascii")
    if len(version_bytes) > 24:
        raise ValueError("rulespec version does not fit in solution shard header")
    header[offset : offset + len(version_bytes)] = version_bytes

    with destination.open("wb") as handle:
        handle.write(header)
        for index, record in enumerate(records):
            if record.local_id != index:
                raise ValueError("solution records must be written in ascending local_id order")
            handle.write(
                SOLUTION_RECORD.pack(
                    _OUTCOME_TO_CODE[record.outcome],
                    UNKNOWN_MOVE_CODE if record.best_move_code is None else int(record.best_move_code),
                    UNKNOWN_DISTANCE if record.distance is None else int(record.distance),
                    _flags(record),
                    0,
                )
            )
    return destination


def parse_solution_header(raw: bytes) -> NativeShardHeader:
    return parse_native_header(raw, SOLUTION_MAGIC)


def decode_solution_record(raw: bytes, local_id: int) -> NativeSolutionRecord:
    header = parse_solution_header(raw)
    if local_id < 0 or local_id >= header.record_count:
        raise ValueError(f"local_id must be between 0 and {header.record_count - 1}, got {local_id}")
    offset = HEADER.size + local_id * SOLUTION_RECORD.size
    return _record_from_tuple(local_id, SOLUTION_RECORD.unpack_from(raw, offset))


def decode_all_solution_records(raw: bytes) -> list[NativeSolutionRecord]:
    header = parse_solution_header(raw)
    records: list[NativeSolutionRecord] = []
    for local_id in range(header.record_count):
        offset = HEADER.size + local_id * SOLUTION_RECORD.size
        records.append(_record_from_tuple(local_id, SOLUTION_RECORD.unpack_from(raw, offset)))
    return records
