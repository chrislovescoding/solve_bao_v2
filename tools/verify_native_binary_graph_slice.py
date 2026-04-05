from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct
import sys


HEADER = struct.Struct("<8sHHHHQQQ24s")
STATE_RECORD = struct.Struct("<16sBBBBIII")
EDGE_RECORD = struct.Struct("<IIHHHBBBB")
TERMINAL_RESULT_ID = 0xFFFFFFFF
STATE_MAGIC = b"BAOSTATE"
EDGE_MAGIC = b"BAOEDGE!"


def player_code(name: str | None) -> int:
    if name is None:
        return 0
    if name == "south":
        return 1
    if name == "north":
        return 2
    raise ValueError(f"Unknown player name: {name}")


def termination_code(name: str | None) -> int:
    if name is None:
        return 0
    mapping = {
        "landed_in_empty": 1,
        "current_player_front_row_empty": 2,
        "opponent_front_row_empty": 3,
        "infinite_move": 4,
    }
    if name not in mapping:
        raise ValueError(f"Unknown termination name: {name}")
    return mapping[name]


def build_state_flags(record: dict[str, object]) -> int:
    flags = 0
    if bool(record["expanded"]):
        flags |= 1 << 0
    flags |= player_code(record.get("state_terminal_winner")) << 1
    return flags


def build_state_terminal_outcome_code(record: dict[str, object]) -> int:
    outcome = record.get("state_terminal_outcome")
    if outcome is None and record.get("state_terminal_winner") is not None:
        outcome = "loss"
    mapping = {
        None: 0,
        "win": 1,
        "loss": 2,
        "draw": 3,
    }
    if outcome not in mapping:
        raise ValueError(f"Unknown state terminal outcome: {outcome}")
    return mapping[outcome]


def build_state_terminal_distance(record: dict[str, object]) -> int:
    distance = record.get("state_terminal_distance")
    if distance is None and record.get("state_terminal_winner") is not None:
        return 0
    if distance is None:
        return 0xFF
    return int(distance)


def build_edge_flags(record: dict[str, object]) -> int:
    flags = 0
    if record["move_kind"] == "mtaji":
        flags |= 1 << 0
    if bool(record["infinite_move"]):
        flags |= 1 << 1
    flags |= termination_code(record.get("termination")) << 2
    flags |= player_code(record.get("terminal_winner")) << 5
    return flags


def load_jsonl(path: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    with path.open("r", encoding="ascii") as handle:
        for line in handle:
            if line.strip():
                records.append(json.loads(line))
    return records


def parse_header(raw: bytes, expected_magic: bytes, expected_record_size: int) -> tuple[int, int]:
    if len(raw) < HEADER.size:
        raise AssertionError("Binary shard is smaller than the fixed header size.")
    (
        magic,
        format_version,
        header_bytes,
        record_bytes,
        _depth_limit,
        record_count,
        payload_bytes,
        aux_count,
        rulespec_version_bytes,
    ) = HEADER.unpack_from(raw, 0)
    if magic != expected_magic:
        raise AssertionError(f"Unexpected shard magic. expected={expected_magic!r} actual={magic!r}")
    if format_version != 1:
        raise AssertionError(f"Unexpected shard format version: {format_version}")
    if header_bytes != HEADER.size:
        raise AssertionError(f"Unexpected header size field: {header_bytes}")
    if record_bytes != expected_record_size:
        raise AssertionError(f"Unexpected record size field: {record_bytes}")
    if payload_bytes != len(raw) - HEADER.size:
        raise AssertionError(
            f"Header payload_bytes mismatch. expected={len(raw) - HEADER.size} actual={payload_bytes}"
        )
    version = rulespec_version_bytes.rstrip(b"\x00").decode("ascii")
    if version != "rulespec-v1.0.0-draft":
        raise AssertionError(f"Unexpected rulespec version in header: {version}")
    return int(record_count), int(aux_count)


def verify_states(state_jsonl: Path, state_binary: Path) -> tuple[int, int]:
    json_records = load_jsonl(state_jsonl)
    raw = state_binary.read_bytes()
    record_count, expanded_state_count = parse_header(raw, STATE_MAGIC, STATE_RECORD.size)
    if record_count != len(json_records):
        raise AssertionError(f"State count mismatch. header={record_count} json={len(json_records)}")

    payload = raw[HEADER.size :]
    if len(payload) % STATE_RECORD.size != 0:
        raise AssertionError("State payload length is not a multiple of the record size.")

    actual_expanded = 0
    for index, record in enumerate(json_records):
        unpacked = STATE_RECORD.unpack_from(payload, index * STATE_RECORD.size)
        expected = (
            bytes.fromhex(str(record["canonical_state_key_hex"])),
            int(record["depth"]),
            build_state_flags(record),
            build_state_terminal_outcome_code(record),
            build_state_terminal_distance(record),
            int(record["outdegree"]),
            int(record["nonterminal_successor_count"]),
            int(record["terminal_move_count"]),
        )
        if unpacked != expected:
            raise AssertionError(f"State record mismatch at index {index}. expected={expected} actual={unpacked}")
        if bool(record["expanded"]):
            actual_expanded += 1

    if actual_expanded != expanded_state_count:
        raise AssertionError(
            f"Expanded state count mismatch. header={expanded_state_count} actual={actual_expanded}"
        )
    return record_count, actual_expanded


def verify_edges(state_jsonl: Path, edge_jsonl: Path, edge_binary: Path) -> tuple[int, int]:
    state_records = load_jsonl(state_jsonl)
    edge_records = load_jsonl(edge_jsonl)
    key_to_id = {str(record["canonical_state_key_hex"]): index for index, record in enumerate(state_records)}

    raw = edge_binary.read_bytes()
    record_count, terminal_edge_count = parse_header(raw, EDGE_MAGIC, EDGE_RECORD.size)
    if record_count != len(edge_records):
        raise AssertionError(f"Edge count mismatch. header={record_count} json={len(edge_records)}")

    payload = raw[HEADER.size :]
    if len(payload) % EDGE_RECORD.size != 0:
        raise AssertionError("Edge payload length is not a multiple of the record size.")

    actual_terminal = 0
    for index, record in enumerate(edge_records):
        result_key = record.get("result_state_key_hex")
        expected = (
            key_to_id[str(record["source_state_key_hex"])],
            TERMINAL_RESULT_ID if result_key is None else key_to_id[str(result_key)],
            int(record["sowings"]),
            int(record["seeds_sown"]),
            int(record["captures"]),
            int(record["move_code"]),
            int(record["source_depth"]),
            build_edge_flags(record),
            0,
        )
        unpacked = EDGE_RECORD.unpack_from(payload, index * EDGE_RECORD.size)
        if unpacked != expected:
            raise AssertionError(f"Edge record mismatch at index {index}. expected={expected} actual={unpacked}")
        if record.get("terminal_winner") is not None:
            actual_terminal += 1

    if actual_terminal != terminal_edge_count:
        raise AssertionError(
            f"Terminal edge count mismatch. header={terminal_edge_count} actual={actual_terminal}"
        )
    return record_count, actual_terminal


def main(state_jsonl: Path, state_binary: Path, edge_jsonl: Path, edge_binary: Path) -> int:
    state_count, expanded_states = verify_states(state_jsonl, state_binary)
    edge_count, terminal_edges = verify_edges(state_jsonl, edge_jsonl, edge_binary)
    print(f"validated_state_records={state_count}")
    print(f"validated_edge_records={edge_count}")
    print(f"expanded_states={expanded_states}")
    print(f"terminal_edges={terminal_edges}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-jsonl", type=Path, default=Path("artifacts/shards/state_slice_depth6.jsonl"))
    parser.add_argument(
        "--state-binary",
        type=Path,
        default=Path("artifacts/shards/native_state_slice_depth6.bin"),
    )
    parser.add_argument("--edge-jsonl", type=Path, default=Path("artifacts/shards/edge_slice_depth6.jsonl"))
    parser.add_argument(
        "--edge-binary",
        type=Path,
        default=Path("artifacts/shards/native_edge_slice_depth6.bin"),
    )
    args = parser.parse_args()
    sys.exit(main(args.state_jsonl, args.state_binary, args.edge_jsonl, args.edge_binary))
