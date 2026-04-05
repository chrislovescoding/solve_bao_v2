from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct
import sys


HEADER = struct.Struct("<8sHHHHQQQ24s")
ADJ_RECORD = struct.Struct("<IHHBBBB")
OFFSET = struct.Struct("<I")
TERMINAL_RESULT_ID = 0xFFFFFFFF
ADJ_MAGIC = b"BAOADJ!!"


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


def main(state_jsonl: Path, edge_jsonl: Path, adjacency_binary: Path) -> int:
    state_records = load_jsonl(state_jsonl)
    edge_records = load_jsonl(edge_jsonl)
    key_to_id = {str(record["canonical_state_key_hex"]): index for index, record in enumerate(state_records)}
    raw = adjacency_binary.read_bytes()
    if len(raw) < HEADER.size:
        raise AssertionError("Adjacency shard is smaller than the fixed header size.")

    (
        magic,
        format_version,
        header_bytes,
        record_bytes,
        _depth_limit,
        record_count,
        payload_bytes,
        state_count,
        rulespec_version_bytes,
    ) = HEADER.unpack_from(raw, 0)
    if magic != ADJ_MAGIC:
        raise AssertionError(f"Unexpected adjacency shard magic: {magic!r}")
    if format_version != 1:
        raise AssertionError(f"Unexpected adjacency format version: {format_version}")
    if header_bytes != HEADER.size:
        raise AssertionError(f"Unexpected adjacency header size: {header_bytes}")
    if record_bytes != ADJ_RECORD.size:
        raise AssertionError(f"Unexpected adjacency edge record size: {record_bytes}")
    version = rulespec_version_bytes.rstrip(b"\x00").decode("ascii")
    if version != "rulespec-v1.0.0-draft":
        raise AssertionError(f"Unexpected rulespec version in adjacency header: {version}")
    if record_count != len(edge_records):
        raise AssertionError(f"Adjacency edge count mismatch. header={record_count} json={len(edge_records)}")
    if state_count != len(state_records):
        raise AssertionError(f"Adjacency state count mismatch. header={state_count} json={len(state_records)}")
    if payload_bytes != len(raw) - HEADER.size:
        raise AssertionError(
            f"Adjacency payload_bytes mismatch. expected={len(raw) - HEADER.size} actual={payload_bytes}"
        )

    offset_count = len(state_records) + 1
    offset_table_bytes = offset_count * OFFSET.size
    payload = raw[HEADER.size :]
    if len(payload) < offset_table_bytes:
        raise AssertionError("Adjacency payload is smaller than the offset table.")

    offsets_raw = payload[:offset_table_bytes]
    edge_payload = payload[offset_table_bytes:]
    if len(edge_payload) != len(edge_records) * ADJ_RECORD.size:
        raise AssertionError(
            f"Adjacency edge payload size mismatch. expected={len(edge_records) * ADJ_RECORD.size} actual={len(edge_payload)}"
        )

    offsets = [OFFSET.unpack_from(offsets_raw, index * OFFSET.size)[0] for index in range(offset_count)]
    expected_offsets = [0] * offset_count
    for record in edge_records:
        source_id = key_to_id[str(record["source_state_key_hex"])]
        expected_offsets[source_id + 1] += 1
    for index in range(1, offset_count):
        expected_offsets[index] += expected_offsets[index - 1]
    if offsets != expected_offsets:
        raise AssertionError("Adjacency offset table does not match grouped edge counts.")

    for index, record in enumerate(edge_records):
        result_key = record.get("result_state_key_hex")
        expected = (
            TERMINAL_RESULT_ID if result_key is None else key_to_id[str(result_key)],
            int(record["sowings"]),
            int(record["seeds_sown"]),
            int(record["captures"]),
            int(record["move_code"]),
            build_edge_flags(record),
            0,
        )
        unpacked = ADJ_RECORD.unpack_from(edge_payload, index * ADJ_RECORD.size)
        if unpacked != expected:
            raise AssertionError(f"Adjacency edge record mismatch at index {index}. expected={expected} actual={unpacked}")

    print(f"validated_state_records={len(state_records)}")
    print(f"validated_edge_records={len(edge_records)}")
    print(f"offset_entries={offset_count}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-jsonl", type=Path, default=Path("artifacts/shards/state_slice_depth6.jsonl"))
    parser.add_argument("--edge-jsonl", type=Path, default=Path("artifacts/shards/edge_slice_depth6.jsonl"))
    parser.add_argument(
        "--adjacency-binary",
        type=Path,
        default=Path("artifacts/shards/native_adjacency_slice_depth6.bin"),
    )
    args = parser.parse_args()
    sys.exit(main(args.state_jsonl, args.edge_jsonl, args.adjacency_binary))
