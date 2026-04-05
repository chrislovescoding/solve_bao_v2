from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct
import sys


STATE_RECORD = struct.Struct("<16sBBHIII")
EDGE_RECORD = struct.Struct("<IIHHHBBBB")
TERMINAL_RESULT_ID = 0xFFFFFFFF


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


def verify_states(state_jsonl: Path, state_binary: Path) -> tuple[int, dict[str, int]]:
    json_records = load_jsonl(state_jsonl)
    raw = state_binary.read_bytes()
    if len(raw) % STATE_RECORD.size != 0:
        raise AssertionError("State binary payload length is not a multiple of the record size.")

    record_count = len(raw) // STATE_RECORD.size
    if record_count != len(json_records):
        raise AssertionError(f"State count mismatch. binary={record_count} json={len(json_records)}")

    expanded_states = 0
    for index, record in enumerate(json_records):
        unpacked = STATE_RECORD.unpack_from(raw, index * STATE_RECORD.size)
        expected = (
            bytes.fromhex(str(record["canonical_state_key_hex"])),
            int(record["depth"]),
            build_state_flags(record),
            0,
            int(record["outdegree"]),
            int(record["nonterminal_successor_count"]),
            int(record["terminal_move_count"]),
        )
        if unpacked != expected:
            raise AssertionError(f"State record mismatch at index {index}. expected={expected} actual={unpacked}")
        if bool(record["expanded"]):
            expanded_states += 1

    return record_count, {"expanded_states": expanded_states}


def verify_edges(
    state_jsonl: Path,
    edge_jsonl: Path,
    edge_binary: Path,
) -> tuple[int, dict[str, int]]:
    state_records = load_jsonl(state_jsonl)
    edge_records = load_jsonl(edge_jsonl)
    key_to_id = {str(record["canonical_state_key_hex"]): index for index, record in enumerate(state_records)}

    raw = edge_binary.read_bytes()
    if len(raw) % EDGE_RECORD.size != 0:
        raise AssertionError("Edge binary payload length is not a multiple of the record size.")

    record_count = len(raw) // EDGE_RECORD.size
    if record_count != len(edge_records):
        raise AssertionError(f"Edge count mismatch. binary={record_count} json={len(edge_records)}")

    terminal_edges = 0
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
        unpacked = EDGE_RECORD.unpack_from(raw, index * EDGE_RECORD.size)
        if unpacked != expected:
            raise AssertionError(f"Edge record mismatch at index {index}. expected={expected} actual={unpacked}")
        if record.get("terminal_winner") is not None:
            terminal_edges += 1

    return record_count, {"terminal_edges": terminal_edges}


def main(state_jsonl: Path, state_binary: Path, edge_jsonl: Path, edge_binary: Path) -> int:
    state_count, state_stats = verify_states(state_jsonl, state_binary)
    edge_count, edge_stats = verify_edges(state_jsonl, edge_jsonl, edge_binary)
    print(f"validated_state_records={state_count}")
    print(f"validated_edge_records={edge_count}")
    print(f"expanded_states={state_stats['expanded_states']}")
    print(f"terminal_edges={edge_stats['terminal_edges']}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-jsonl", type=Path, default=Path("artifacts/shards/state_slice_depth6.jsonl"))
    parser.add_argument("--state-binary", type=Path, default=Path("artifacts/shards/state_slice_depth6.bin"))
    parser.add_argument("--edge-jsonl", type=Path, default=Path("artifacts/shards/edge_slice_depth6.jsonl"))
    parser.add_argument("--edge-binary", type=Path, default=Path("artifacts/shards/edge_slice_depth6.bin"))
    args = parser.parse_args()
    sys.exit(main(args.state_jsonl, args.state_binary, args.edge_jsonl, args.edge_binary))
