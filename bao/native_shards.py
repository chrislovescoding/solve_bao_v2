from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import struct


HEADER = struct.Struct("<8sHHHHQQQ24s")
STATE_RECORD = struct.Struct("<16sBBBBIII")
ADJ_RECORD = struct.Struct("<IHHBBBB")
OFFSET = struct.Struct("<I")

STATE_MAGIC = b"BAOSTATE"
ADJ_MAGIC = b"BAOADJ!!"
TERMINAL_RESULT_ID = 0xFFFFFFFF

_PLAYER_BY_CODE = {0: None, 1: "south", 2: "north"}
_OUTCOME_BY_CODE = {0: None, 1: "win", 2: "loss", 3: "draw"}
_TERMINATION_BY_CODE = {
    0: None,
    1: "landed_in_empty",
    2: "current_player_front_row_empty",
    3: "opponent_front_row_empty",
    4: "infinite_move",
}


@dataclass(frozen=True)
class NativeShardHeader:
    magic: str
    format_version: int
    header_bytes: int
    record_bytes: int
    depth: int
    record_count: int
    payload_bytes: int
    aux_count: int
    rulespec_version: str

    def to_dict(self) -> dict[str, object]:
        return {
            "magic": self.magic,
            "format_version": self.format_version,
            "header_bytes": self.header_bytes,
            "record_bytes": self.record_bytes,
            "depth": self.depth,
            "record_count": self.record_count,
            "payload_bytes": self.payload_bytes,
            "aux_count": self.aux_count,
            "rulespec_version": self.rulespec_version,
        }


@dataclass(frozen=True)
class NativeStateRecord:
    local_id: int
    canonical_state_key_hex: str
    depth: int
    expanded: bool
    terminal_winner: str | None
    terminal_outcome: str | None
    terminal_distance: int | None
    outdegree: int
    nonterminal_successor_count: int
    terminal_move_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "local_id": self.local_id,
            "canonical_state_key_hex": self.canonical_state_key_hex,
            "depth": self.depth,
            "expanded": self.expanded,
            "terminal_winner": self.terminal_winner,
            "terminal_outcome": self.terminal_outcome,
            "terminal_distance": self.terminal_distance,
            "outdegree": self.outdegree,
            "nonterminal_successor_count": self.nonterminal_successor_count,
            "terminal_move_count": self.terminal_move_count,
        }


@dataclass(frozen=True)
class NativeAdjacencyRecord:
    edge_index: int
    result_local_id: int | None
    result_state_key_hex: str | None
    sowings: int
    seeds_sown: int
    captures: int
    move_code: int
    move_kind: str
    infinite_move: bool
    termination: str | None
    terminal_winner: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "edge_index": self.edge_index,
            "result_local_id": self.result_local_id,
            "result_state_key_hex": self.result_state_key_hex,
            "sowings": self.sowings,
            "seeds_sown": self.seeds_sown,
            "captures": self.captures,
            "move_code": self.move_code,
            "move_kind": self.move_kind,
            "infinite_move": self.infinite_move,
            "termination": self.termination,
            "terminal_winner": self.terminal_winner,
        }


def load_shard_bytes(path: Path) -> bytes:
    return path.read_bytes()


def parse_native_header(raw: bytes, expected_magic: bytes) -> NativeShardHeader:
    if len(raw) < HEADER.size:
        raise ValueError("binary shard is smaller than the fixed header size")
    magic, format_version, header_bytes, record_bytes, depth, record_count, payload_bytes, aux_count, rulespec = (
        HEADER.unpack_from(raw, 0)
    )
    if magic != expected_magic:
        raise ValueError(f"unexpected shard magic: {magic!r}")
    return NativeShardHeader(
        magic=magic.decode("ascii"),
        format_version=int(format_version),
        header_bytes=int(header_bytes),
        record_bytes=int(record_bytes),
        depth=int(depth),
        record_count=int(record_count),
        payload_bytes=int(payload_bytes),
        aux_count=int(aux_count),
        rulespec_version=rulespec.rstrip(b"\x00").decode("ascii"),
    )


def _player_from_flags(flags: int) -> str | None:
    return _PLAYER_BY_CODE.get((flags >> 1) & 0b11, None)


def _termination_from_flags(flags: int) -> str | None:
    return _TERMINATION_BY_CODE.get((flags >> 2) & 0b111, None)


def _edge_terminal_from_flags(flags: int) -> str | None:
    return _PLAYER_BY_CODE.get((flags >> 5) & 0b11, None)


def _outcome_from_code(code: int) -> str | None:
    return _OUTCOME_BY_CODE.get(code, None)


def _state_record_offset(local_id: int) -> int:
    return HEADER.size + local_id * STATE_RECORD.size


def _adjacency_offsets_start() -> int:
    return HEADER.size


def _normalize_state_key_bytes(state_key: bytes | str) -> bytes:
    if isinstance(state_key, str):
        state_key = bytes.fromhex(state_key)
    if len(state_key) != 16:
        raise ValueError("state key must be exactly 16 bytes")
    return state_key


def decode_native_state_record(raw: bytes, local_id: int) -> NativeStateRecord:
    header = parse_native_header(raw, STATE_MAGIC)
    if local_id < 0 or local_id >= header.record_count:
        raise ValueError(f"local_id must be between 0 and {header.record_count - 1}, got {local_id}")
    key_bytes, depth, flags, terminal_outcome_code, terminal_distance_raw, outdegree, nonterminal_successor_count, terminal_move_count = STATE_RECORD.unpack_from(
        raw,
        _state_record_offset(local_id),
    )
    terminal_distance = None if terminal_distance_raw == 0xFF else int(terminal_distance_raw)
    return NativeStateRecord(
        local_id=local_id,
        canonical_state_key_hex=key_bytes.hex(),
        depth=int(depth),
        expanded=bool(flags & 1),
        terminal_winner=_player_from_flags(flags),
        terminal_outcome=_outcome_from_code(int(terminal_outcome_code)),
        terminal_distance=terminal_distance,
        outdegree=int(outdegree),
        nonterminal_successor_count=int(nonterminal_successor_count),
        terminal_move_count=int(terminal_move_count),
    )


def decode_all_native_state_records(raw: bytes) -> list[NativeStateRecord]:
    header = parse_native_header(raw, STATE_MAGIC)
    records: list[NativeStateRecord] = []
    for local_id in range(header.record_count):
        key_bytes, depth, flags, terminal_outcome_code, terminal_distance_raw, outdegree, nonterminal_successor_count, terminal_move_count = (
            STATE_RECORD.unpack_from(raw, _state_record_offset(local_id))
        )
        terminal_distance = None if terminal_distance_raw == 0xFF else int(terminal_distance_raw)
        records.append(
            NativeStateRecord(
                local_id=local_id,
                canonical_state_key_hex=key_bytes.hex(),
                depth=int(depth),
                expanded=bool(flags & 1),
                terminal_winner=_player_from_flags(flags),
                terminal_outcome=_outcome_from_code(int(terminal_outcome_code)),
                terminal_distance=terminal_distance,
                outdegree=int(outdegree),
                nonterminal_successor_count=int(nonterminal_successor_count),
                terminal_move_count=int(terminal_move_count),
            )
        )
    return records


def state_key_bytes_at_local_id(raw: bytes, local_id: int) -> bytes:
    header = parse_native_header(raw, STATE_MAGIC)
    if local_id < 0 or local_id >= header.record_count:
        raise ValueError(f"local_id must be between 0 and {header.record_count - 1}, got {local_id}")
    offset = _state_record_offset(local_id)
    return STATE_RECORD.unpack_from(raw, offset)[0]


def find_local_id_by_state_key(raw: bytes, state_key: bytes | str) -> int | None:
    header = parse_native_header(raw, STATE_MAGIC)
    target = _normalize_state_key_bytes(state_key)
    low = 0
    high = header.record_count
    while low < high:
        mid = (low + high) // 2
        current = state_key_bytes_at_local_id(raw, mid)
        if current < target:
            low = mid + 1
        else:
            high = mid
    if low < header.record_count and state_key_bytes_at_local_id(raw, low) == target:
        return low
    return None


def adjacency_offsets(raw: bytes) -> list[int]:
    header = parse_native_header(raw, ADJ_MAGIC)
    offset_count = header.aux_count + 1
    start = _adjacency_offsets_start()
    return [OFFSET.unpack_from(raw, start + index * OFFSET.size)[0] for index in range(offset_count)]


def adjacency_edge_payload(raw: bytes) -> bytes:
    header = parse_native_header(raw, ADJ_MAGIC)
    offset_table_bytes = (header.aux_count + 1) * OFFSET.size
    return raw[HEADER.size + offset_table_bytes :]


def decode_native_adjacency_records(
    state_raw: bytes,
    adjacency_raw: bytes,
    local_id: int,
) -> list[NativeAdjacencyRecord]:
    state_header = parse_native_header(state_raw, STATE_MAGIC)
    adjacency_header = parse_native_header(adjacency_raw, ADJ_MAGIC)
    if adjacency_header.aux_count != state_header.record_count:
        raise ValueError("adjacency aux_count does not match state count")
    if local_id < 0 or local_id >= state_header.record_count:
        raise ValueError(f"local_id must be between 0 and {state_header.record_count - 1}, got {local_id}")

    offsets = adjacency_offsets(adjacency_raw)
    edge_payload = adjacency_edge_payload(adjacency_raw)
    start = offsets[local_id]
    end = offsets[local_id + 1]

    records: list[NativeAdjacencyRecord] = []
    for edge_index in range(start, end):
        result_id, sowings, seeds_sown, captures, move_code, flags, _reserved = ADJ_RECORD.unpack_from(
            edge_payload,
            edge_index * ADJ_RECORD.size,
        )
        result_local_id = None if result_id == TERMINAL_RESULT_ID else int(result_id)
        result_state_key_hex = None
        if result_local_id is not None:
            result_state_key_hex = state_key_bytes_at_local_id(state_raw, result_local_id).hex()
        records.append(
            NativeAdjacencyRecord(
                edge_index=edge_index,
                result_local_id=result_local_id,
                result_state_key_hex=result_state_key_hex,
                sowings=int(sowings),
                seeds_sown=int(seeds_sown),
                captures=int(captures),
                move_code=int(move_code),
                move_kind="mtaji" if (flags & 1) else "takasa",
                infinite_move=bool(flags & (1 << 1)),
                termination=_termination_from_flags(flags),
                terminal_winner=_edge_terminal_from_flags(flags),
            )
        )
    return records


def decode_all_native_adjacency_records(
    state_raw: bytes,
    adjacency_raw: bytes,
    *,
    state_records: list[NativeStateRecord] | None = None,
) -> list[list[NativeAdjacencyRecord]]:
    state_header = parse_native_header(state_raw, STATE_MAGIC)
    adjacency_header = parse_native_header(adjacency_raw, ADJ_MAGIC)
    if adjacency_header.aux_count != state_header.record_count:
        raise ValueError("adjacency aux_count does not match state count")

    if state_records is None:
        state_records = decode_all_native_state_records(state_raw)
    state_key_hex_by_id = [record.canonical_state_key_hex for record in state_records]

    offsets = adjacency_offsets(adjacency_raw)
    edge_payload = adjacency_edge_payload(adjacency_raw)
    grouped: list[list[NativeAdjacencyRecord]] = []
    for local_id in range(state_header.record_count):
        start = offsets[local_id]
        end = offsets[local_id + 1]
        local_records: list[NativeAdjacencyRecord] = []
        for edge_index in range(start, end):
            result_id, sowings, seeds_sown, captures, move_code, flags, _reserved = ADJ_RECORD.unpack_from(
                edge_payload,
                edge_index * ADJ_RECORD.size,
            )
            result_local_id = None if result_id == TERMINAL_RESULT_ID else int(result_id)
            result_state_key_hex = None
            if result_local_id is not None:
                result_state_key_hex = state_key_hex_by_id[result_local_id]
            local_records.append(
                NativeAdjacencyRecord(
                    edge_index=edge_index,
                    result_local_id=result_local_id,
                    result_state_key_hex=result_state_key_hex,
                    sowings=int(sowings),
                    seeds_sown=int(seeds_sown),
                    captures=int(captures),
                    move_code=int(move_code),
                    move_kind="mtaji" if (flags & 1) else "takasa",
                    infinite_move=bool(flags & (1 << 1)),
                    termination=_termination_from_flags(flags),
                    terminal_winner=_edge_terminal_from_flags(flags),
                )
            )
        grouped.append(local_records)
    return grouped


def query_native_state_successors(
    state_raw: bytes,
    adjacency_raw: bytes,
    *,
    local_id: int | None = None,
    state_key: bytes | str | None = None,
) -> dict[str, object]:
    if (local_id is None) == (state_key is None):
        raise ValueError("exactly one of local_id or state_key must be provided")

    resolved_local_id = local_id
    if resolved_local_id is None:
        resolved_local_id = find_local_id_by_state_key(state_raw, state_key)
        if resolved_local_id is None:
            raise ValueError("state key was not found in the state shard")

    state = decode_native_state_record(state_raw, resolved_local_id)
    successors = decode_native_adjacency_records(state_raw, adjacency_raw, resolved_local_id)
    return {
        "state_header": parse_native_header(state_raw, STATE_MAGIC).to_dict(),
        "adjacency_header": parse_native_header(adjacency_raw, ADJ_MAGIC).to_dict(),
        "state": state.to_dict(),
        "successor_count": len(successors),
        "successors": [record.to_dict() for record in successors],
    }
