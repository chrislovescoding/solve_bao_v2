from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bao import (
    NativeSolutionRecord,
    SolverMove,
    decode_all_native_adjacency_records,
    decode_all_native_state_records,
    load_shard_bytes,
    parse_native_header,
    solve_via_scc,
    write_solution_shard,
)
from bao.solution_shards import SOLUTION_RECORD


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
        "artifact_type": "solution_shard_binary_v1_scc_slice",
        "rulespec_version": "rulespec-v1.0.0-draft",
        "code_revision": "workspace-unversioned",
        "item_count": item_count,
        "payload_bytes": payload_path.stat().st_size,
        "sha256": sha256_path(payload_path),
        "notes": [
            f"depth={depth}",
            "source=scc_slice_solver",
            "representation=local_id_aligned_solution_records",
            f"record_size={SOLUTION_RECORD.size}",
            f"resolved_records={resolved_count}",
            "expanded nodes solved via SCC condensation with frontier states treated as external unknowns",
        ],
    }
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="ascii")


def main(
    state_binary: Path,
    adjacency_binary: Path,
    graph_summary: Path | None,
    output: Path,
    solution_output: Path,
    solution_manifest: Path,
    scc_summary_output: Path,
) -> int:
    state_raw = load_shard_bytes(state_binary)
    adjacency_raw = load_shard_bytes(adjacency_binary)
    state_header = parse_native_header(state_raw, b"BAOSTATE")
    adjacency_header = parse_native_header(adjacency_raw, b"BAOADJ!!")
    if adjacency_header.aux_count != state_header.record_count:
        raise ValueError("state and adjacency shard counts do not match")

    states = decode_all_native_state_records(state_raw)
    successors = decode_all_native_adjacency_records(state_raw, adjacency_raw, state_records=states)
    expanded_local_ids = [state.local_id for state in states if state.expanded]
    dense_index_by_local = {local_id: index for index, local_id in enumerate(expanded_local_ids)}

    solver_moves: list[list[SolverMove]] = []
    for local_id in expanded_local_ids:
        local_moves: list[SolverMove] = []
        for edge in successors[local_id]:
            if edge.terminal_winner == "south":
                local_moves.append(SolverMove(move_code=edge.move_code, kind="win"))
            elif edge.terminal_winner == "north":
                local_moves.append(SolverMove(move_code=edge.move_code, kind="loss"))
            elif edge.result_local_id is None:
                local_moves.append(SolverMove(move_code=edge.move_code, kind="unknown"))
            elif not states[edge.result_local_id].expanded:
                local_moves.append(SolverMove(move_code=edge.move_code, kind="unknown"))
            else:
                local_moves.append(
                    SolverMove(
                        move_code=edge.move_code,
                        kind="node",
                        target=dense_index_by_local[edge.result_local_id],
                    )
                )
        solver_moves.append(local_moves)

    scc_result = solve_via_scc(solver_moves)
    dense_component_stats = {record.component_id: record for record in scc_result.component_stats}

    full_solution_records: list[NativeSolutionRecord] = []
    resolved_count = 0
    dense_result_by_local: dict[int, tuple[int, object]] = {}
    for dense_index, local_id in enumerate(expanded_local_ids):
        dense_result_by_local[local_id] = (dense_index, scc_result.node_results[dense_index])

    for state in states:
        if state.terminal_outcome is not None:
            record = NativeSolutionRecord(
                local_id=state.local_id,
                outcome=state.terminal_outcome,
                best_move_code=None,
                distance=state.terminal_distance,
                partial=False,
                terminal_seed=True,
                frontier_dependent=False,
            )
        elif state.local_id in dense_result_by_local:
            dense_index, dense_result = dense_result_by_local[state.local_id]
            component_id = scc_result.component_ids[dense_index]
            component_stat = dense_component_stats[component_id]
            unresolved = dense_result.outcome is None
            record = NativeSolutionRecord(
                local_id=state.local_id,
                outcome=dense_result.outcome,
                best_move_code=dense_result.best_move_code,
                distance=dense_result.distance,
                partial=unresolved,
                terminal_seed=False,
                frontier_dependent=unresolved and component_stat.frontier_edge_count > 0,
            )
        else:
            record = NativeSolutionRecord(
                local_id=state.local_id,
                outcome=None,
                best_move_code=None,
                distance=None,
                partial=True,
                terminal_seed=False,
                frontier_dependent=True,
            )
        if record.outcome is not None:
            resolved_count += 1
        full_solution_records.append(record)

    write_solution_shard(
        solution_output,
        full_solution_records,
        depth=state_header.depth,
        resolved_count=resolved_count,
        rulespec_version=state_header.rulespec_version,
    )
    write_manifest(
        solution_manifest,
        solution_output,
        item_count=len(full_solution_records),
        resolved_count=resolved_count,
        depth=state_header.depth,
    )

    graph = {}
    if graph_summary and graph_summary.exists():
        graph = json.loads(graph_summary.read_text(encoding="ascii"))

    largest_component = max((len(component) for component in scc_result.components), default=0)
    unresolved_components = [record for record in scc_result.component_stats if record.unresolved_count > 0]
    frontier_dependent_components = [record for record in unresolved_components if record.frontier_edge_count > 0]
    closed_unresolved_components = [record for record in unresolved_components if record.frontier_edge_count == 0]

    root_local_id = graph.get("root_local_id")
    root_state_key_hex = graph.get("root_state_key_hex")
    root_status = None
    root_best_move_code = None
    root_distance = None
    if root_local_id is not None:
        root_local_id = int(root_local_id)
        root_record = full_solution_records[root_local_id]
        root_status = root_record.outcome or "unknown"
        root_best_move_code = root_record.best_move_code
        root_distance = root_record.distance

    summary = {
        "rulespec_version": state_header.rulespec_version,
        "depth": state_header.depth,
        "state_count": state_header.record_count,
        "expanded_state_count": len(expanded_local_ids),
        "frontier_state_count": sum(1 for state in states if not state.expanded and state.terminal_outcome is None),
        "edge_count": adjacency_header.record_count,
        "solution_record_bytes": SOLUTION_RECORD.size,
        "resolved_win_count": sum(1 for record in full_solution_records if record.outcome == "win"),
        "resolved_loss_count": sum(1 for record in full_solution_records if record.outcome == "loss"),
        "resolved_state_count": resolved_count,
        "unknown_state_count": sum(1 for record in full_solution_records if record.outcome is None),
        "component_count": len(scc_result.components),
        "largest_component_size": largest_component,
        "unresolved_component_count": len(unresolved_components),
        "frontier_dependent_component_count": len(frontier_dependent_components),
        "closed_unresolved_component_count": len(closed_unresolved_components),
        "root_local_id": root_local_id,
        "root_state_key_hex": root_state_key_hex,
        "root_status": root_status,
        "root_best_move_code": root_best_move_code,
        "root_distance": root_distance,
        "notes": [
            "expanded nodes solved through SCC condensation and component-local fixpoint propagation",
            "unexpanded frontier states treated as external unknowns",
            "closed unresolved components indicate cycle structure that is not forced by the current finite slice",
        ],
        "top_components_by_size": [
            record.to_dict()
            for record in sorted(scc_result.component_stats, key=lambda item: (-item.size, item.component_id))[:10]
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="ascii")

    scc_summary_output.parent.mkdir(parents=True, exist_ok=True)
    scc_payload = {
        "rulespec_version": state_header.rulespec_version,
        "depth": state_header.depth,
        "component_count": len(scc_result.components),
        "component_stats": [record.to_dict() for record in scc_result.component_stats],
        "components": scc_result.components,
    }
    scc_summary_output.write_text(json.dumps(scc_payload, indent=2, sort_keys=True) + "\n", encoding="ascii")

    print(f"output={output}")
    print(f"solution_output={solution_output}")
    print(f"solution_manifest={solution_manifest}")
    print(f"scc_summary={scc_summary_output}")
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
        "--graph-summary",
        type=Path,
        default=Path("artifacts/shards/native_graph_slice_depth6.summary.json"),
        help="Optional graph summary with root metadata.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/solve/slice_scc_depth6.json"),
        help="SCC solve summary JSON output path.",
    )
    parser.add_argument(
        "--solution-output",
        type=Path,
        default=Path("artifacts/solve/slice_scc_depth6.bin"),
        help="SCC solution shard output path.",
    )
    parser.add_argument(
        "--solution-manifest",
        type=Path,
        default=Path("artifacts/solve/slice_scc_depth6.manifest.json"),
        help="Manifest path for the SCC solution shard.",
    )
    parser.add_argument(
        "--scc-summary-output",
        type=Path,
        default=Path("artifacts/analysis/scc_depth6.json"),
        help="Detailed SCC statistics output path.",
    )
    args = parser.parse_args()
    raise SystemExit(
        main(
            args.state_binary,
            args.adjacency_binary,
            args.graph_summary,
            args.output,
            args.solution_output,
            args.solution_manifest,
            args.scc_summary_output,
        )
    )
