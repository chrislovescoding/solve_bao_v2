from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bao.native_shards import (
    decode_all_native_adjacency_records,
    decode_all_native_state_records,
    load_shard_bytes,
    parse_native_header,
)
from bao.solution_shards import NativeSolutionRecord, SOLUTION_RECORD, write_solution_shard


UNKNOWN = "unknown"
WIN = "win"
LOSS = "loss"


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_manifest(
    manifest_path: Path,
    payload_path: Path,
    item_count: int,
    resolved_count: int,
    depth: int,
) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "artifact_type": "solution_shard_binary_v1_partial",
        "rulespec_version": "rulespec-v1.0.0-draft",
        "code_revision": "workspace-unversioned",
        "item_count": item_count,
        "payload_bytes": payload_path.stat().st_size,
        "sha256": sha256_path(payload_path),
        "notes": [
            f"depth={depth}",
            "source=partial_slice_solver",
            "representation=local_id_aligned_solution_records",
            f"record_size={SOLUTION_RECORD.size}",
            f"resolved_records={resolved_count}",
            "unknown records remain frontier-dependent or cycle-dependent within the slice",
        ],
    }
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="ascii")


def solve_partial(
    state_binary: Path,
    adjacency_binary: Path,
    summary_path: Path | None,
) -> tuple[dict[str, object], list[NativeSolutionRecord]]:
    state_raw = load_shard_bytes(state_binary)
    adjacency_raw = load_shard_bytes(adjacency_binary)
    state_header = parse_native_header(state_raw, b"BAOSTATE")
    adjacency_header = parse_native_header(adjacency_raw, b"BAOADJ!!")

    if adjacency_header.aux_count != state_header.record_count:
        raise ValueError("state and adjacency shard counts do not match")

    states = decode_all_native_state_records(state_raw)
    successors = decode_all_native_adjacency_records(state_raw, adjacency_raw, state_records=states)

    statuses = [state.terminal_outcome or UNKNOWN for state in states]
    distances: list[int | None] = [state.terminal_distance for state in states]
    best_move_codes: list[int | None] = [None] * state_header.record_count
    expanded_ids = [state.local_id for state in states if state.expanded and statuses[state.local_id] == UNKNOWN]

    changed = True
    iterations = 0
    while changed:
        changed = False
        iterations += 1
        for local_id in expanded_ids:
            if statuses[local_id] != UNKNOWN:
                continue

            edges = successors[local_id]
            if not edges:
                statuses[local_id] = LOSS
                distances[local_id] = 0
                changed = True
                continue

            winning_candidates: list[tuple[int, int]] = []
            losing_candidates: list[tuple[int, int]] = []
            unresolved = False

            for edge in edges:
                if edge.terminal_winner == "south":
                    winning_candidates.append((1, edge.move_code))
                    continue

                if edge.terminal_winner == "north":
                    losing_candidates.append((1, edge.move_code))
                    continue

                if edge.result_local_id is None:
                    unresolved = True
                    continue

                successor_status = statuses[edge.result_local_id]
                successor_distance = distances[edge.result_local_id]
                if successor_status == LOSS and successor_distance is not None:
                    winning_candidates.append((successor_distance + 1, edge.move_code))
                    continue
                if successor_status == WIN and successor_distance is not None:
                    losing_candidates.append((successor_distance + 1, edge.move_code))
                    continue
                unresolved = True

            if winning_candidates:
                winning_distance, winning_move_code = min(winning_candidates, key=lambda item: (item[0], item[1]))
                statuses[local_id] = WIN
                best_move_codes[local_id] = winning_move_code
                distances[local_id] = winning_distance
                changed = True
            elif not unresolved and len(losing_candidates) == len(edges):
                losing_distance, best_defensive_move = max(losing_candidates, key=lambda item: (item[0], -item[1]))
                statuses[local_id] = LOSS
                best_move_codes[local_id] = best_defensive_move
                distances[local_id] = losing_distance
                changed = True

    summary = {}
    if summary_path and summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="ascii"))

    frontier_state_count = sum(1 for state in states if not state.expanded)
    win_count = sum(1 for status in statuses if status == WIN)
    loss_count = sum(1 for status in statuses if status == LOSS)
    unknown_count = sum(1 for status in statuses if status == UNKNOWN)
    expanded_unknown_count = sum(
        1 for state, status in zip(states, statuses, strict=True) if state.expanded and status == UNKNOWN
    )

    root_local_id = summary.get("root_local_id")
    root_state_key_hex = summary.get("root_state_key_hex")
    root_status = None
    root_best_move_code = None
    root_distance = None
    if root_local_id is not None:
        root_local_id = int(root_local_id)
        root_status = statuses[root_local_id]
        root_best_move_code = best_move_codes[root_local_id]
        root_distance = None if root_status == UNKNOWN else distances[root_local_id]

    solution_records = [
        NativeSolutionRecord(
            local_id=state.local_id,
            outcome=None if statuses[state.local_id] == UNKNOWN else statuses[state.local_id],
            best_move_code=best_move_codes[state.local_id],
            distance=None if statuses[state.local_id] == UNKNOWN else distances[state.local_id],
            partial=statuses[state.local_id] == UNKNOWN,
            terminal_seed=state.terminal_outcome is not None,
            frontier_dependent=statuses[state.local_id] == UNKNOWN,
        )
        for state in states
    ]

    return {
        "rulespec_version": state_header.rulespec_version,
        "depth": state_header.depth,
        "state_count": state_header.record_count,
        "expanded_state_count": sum(1 for state in states if state.expanded),
        "frontier_state_count": frontier_state_count,
        "edge_count": adjacency_header.record_count,
        "solution_record_bytes": SOLUTION_RECORD.size,
        "iterations": iterations,
        "resolved_win_count": win_count,
        "resolved_loss_count": loss_count,
        "resolved_state_count": win_count + loss_count,
        "unknown_state_count": unknown_count,
        "expanded_unknown_count": expanded_unknown_count,
        "root_local_id": root_local_id,
        "root_state_key_hex": root_state_key_hex,
        "root_status": root_status,
        "root_best_move_code": root_best_move_code,
        "root_distance": root_distance,
        "notes": [
            "partial slice solve",
            "frontier states treated as unknown",
            "expanded states only become loss when every legal move is already proven bad inside the slice",
            "resolved states carry a local slice remoteness value measured in plies to termination within the proved subgraph",
        ],
    }, solution_records


def main(
    state_binary: Path,
    adjacency_binary: Path,
    summary_path: Path | None,
    output: Path,
    solution_output: Path,
    solution_manifest: Path,
) -> int:
    result, solution_records = solve_partial(state_binary, adjacency_binary, summary_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="ascii")
    write_solution_shard(
        solution_output,
        solution_records,
        depth=int(result["depth"]),
        resolved_count=int(result["resolved_state_count"]),
        rulespec_version=str(result["rulespec_version"]),
    )
    write_manifest(
        solution_manifest,
        solution_output,
        item_count=len(solution_records),
        resolved_count=int(result["resolved_state_count"]),
        depth=int(result["depth"]),
    )
    print(f"output={output}")
    print(f"solution_output={solution_output}")
    print(f"solution_manifest={solution_manifest}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--state-binary",
        type=Path,
        default=Path("artifacts/shards/native_state_slice_depth6.bin"),
        help="Native binary state shard path.",
    )
    parser.add_argument(
        "--adjacency-binary",
        type=Path,
        default=Path("artifacts/shards/native_adjacency_slice_depth6.bin"),
        help="Native binary adjacency shard path.",
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("artifacts/shards/native_graph_slice_depth6.summary.json"),
        help="Optional native export summary with root metadata.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/solve/slice_partial_depth6.json"),
        help="Partial-solve summary JSON output path.",
    )
    parser.add_argument(
        "--solution-output",
        type=Path,
        default=Path("artifacts/solve/slice_partial_depth6.bin"),
        help="Partial solution shard output path.",
    )
    parser.add_argument(
        "--solution-manifest",
        type=Path,
        default=Path("artifacts/solve/slice_partial_depth6.manifest.json"),
        help="Manifest path for the partial solution shard.",
    )
    args = parser.parse_args()
    raise SystemExit(
        main(
            args.state_binary,
            args.adjacency_binary,
            args.summary,
            args.output,
            args.solution_output,
            args.solution_manifest,
        )
    )
