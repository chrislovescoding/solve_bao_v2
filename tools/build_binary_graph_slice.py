from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct


RULESPEC_VERSION = "rulespec-v1.0.0-draft"
STATE_RECORD = struct.Struct("<16sBBHIII")
EDGE_RECORD = struct.Struct("<IIHHHBBBB")
TERMINAL_RESULT_ID = 0xFFFFFFFF


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_manifest(
    manifest_path: Path,
    artifact_type: str,
    payload_path: Path,
    item_count: int,
    notes: list[str],
) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "artifact_type": artifact_type,
        "rulespec_version": RULESPEC_VERSION,
        "code_revision": "workspace-unversioned",
        "item_count": item_count,
        "payload_bytes": payload_path.stat().st_size,
        "sha256": sha256_path(payload_path),
        "notes": notes,
    }
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="ascii")


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


def main(
    states_jsonl: Path,
    edges_jsonl: Path,
    states_binary: Path,
    states_manifest: Path,
    edges_binary: Path,
    edges_manifest: Path,
    summary_output: Path,
) -> int:
    states: list[dict[str, object]] = []
    with states_jsonl.open("r", encoding="ascii") as handle:
        for line in handle:
            if line.strip():
                states.append(json.loads(line))

    key_to_local_id: dict[str, int] = {}
    for local_id, record in enumerate(states):
        key_hex = str(record["canonical_state_key_hex"])
        key_to_local_id[key_hex] = local_id

    states_binary.parent.mkdir(parents=True, exist_ok=True)
    with states_binary.open("wb") as handle:
        for record in states:
            handle.write(
                STATE_RECORD.pack(
                    bytes.fromhex(str(record["canonical_state_key_hex"])),
                    int(record["depth"]),
                    build_state_flags(record),
                    0,
                    int(record["outdegree"]),
                    int(record["nonterminal_successor_count"]),
                    int(record["terminal_move_count"]),
                )
            )

    edges: list[dict[str, object]] = []
    edges_binary.parent.mkdir(parents=True, exist_ok=True)
    with edges_jsonl.open("r", encoding="ascii") as source, edges_binary.open("wb") as sink:
        for line in source:
            if not line.strip():
                continue
            record = json.loads(line)
            edges.append(record)
            result_key = record.get("result_state_key_hex")
            result_id = TERMINAL_RESULT_ID if result_key is None else key_to_local_id[str(result_key)]
            sink.write(
                EDGE_RECORD.pack(
                    key_to_local_id[str(record["source_state_key_hex"])],
                    result_id,
                    int(record["sowings"]),
                    int(record["seeds_sown"]),
                    int(record["captures"]),
                    int(record["move_code"]),
                    int(record["source_depth"]),
                    build_edge_flags(record),
                    0,
                )
            )

    write_manifest(
        states_manifest,
        "state_shard_binary_v1",
        states_binary,
        len(states),
        [
            "endianness=little",
            f"record_size={STATE_RECORD.size}",
            "local_id_rule=zero_based_record_index",
            f"source_jsonl={states_jsonl}",
        ],
    )
    write_manifest(
        edges_manifest,
        "edge_shard_binary_v1",
        edges_binary,
        len(edges),
        [
            "endianness=little",
            f"record_size={EDGE_RECORD.size}",
            "local_id_rule=zero_based_record_index_in_state_binary",
            f"source_jsonl={edges_jsonl}",
            f"terminal_result_id={TERMINAL_RESULT_ID}",
        ],
    )

    summary = {
        "rulespec_version": RULESPEC_VERSION,
        "state_record_size": STATE_RECORD.size,
        "edge_record_size": EDGE_RECORD.size,
        "state_count": len(states),
        "edge_count": len(edges),
        "state_bytes": states_binary.stat().st_size,
        "edge_bytes": edges_binary.stat().st_size,
        "bytes_per_state": states_binary.stat().st_size / len(states) if states else 0.0,
        "bytes_per_edge": edges_binary.stat().st_size / len(edges) if edges else 0.0,
        "states_binary": str(states_binary),
        "states_manifest": str(states_manifest),
        "edges_binary": str(edges_binary),
        "edges_manifest": str(edges_manifest),
    }
    summary_output.parent.mkdir(parents=True, exist_ok=True)
    summary_output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="ascii")

    print(f"states_binary={states_binary}")
    print(f"states_manifest={states_manifest}")
    print(f"edges_binary={edges_binary}")
    print(f"edges_manifest={edges_manifest}")
    print(f"summary={summary_output}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--states-jsonl",
        type=Path,
        default=Path("artifacts/shards/state_slice_depth6.jsonl"),
        help="Input JSONL state shard.",
    )
    parser.add_argument(
        "--edges-jsonl",
        type=Path,
        default=Path("artifacts/shards/edge_slice_depth6.jsonl"),
        help="Input JSONL edge shard.",
    )
    parser.add_argument(
        "--states-binary",
        type=Path,
        default=Path("artifacts/shards/state_slice_depth6.bin"),
        help="Output binary state shard.",
    )
    parser.add_argument(
        "--states-manifest",
        type=Path,
        default=Path("artifacts/shards/state_slice_depth6.bin.manifest.json"),
        help="Manifest for the binary state shard.",
    )
    parser.add_argument(
        "--edges-binary",
        type=Path,
        default=Path("artifacts/shards/edge_slice_depth6.bin"),
        help="Output binary edge shard.",
    )
    parser.add_argument(
        "--edges-manifest",
        type=Path,
        default=Path("artifacts/shards/edge_slice_depth6.bin.manifest.json"),
        help="Manifest for the binary edge shard.",
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=Path("artifacts/shards/graph_slice_depth6.binary.summary.json"),
        help="Summary JSON path for the binary payloads.",
    )
    args = parser.parse_args()
    raise SystemExit(
        main(
            args.states_jsonl,
            args.edges_jsonl,
            args.states_binary,
            args.states_manifest,
            args.edges_binary,
            args.edges_manifest,
            args.summary_output,
        )
    )
