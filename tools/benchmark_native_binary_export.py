from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time


def main(depth: int, output: Path) -> int:
    command = [
        sys.executable,
        "tools\\export_native_binary_graph_slice.py",
        "--depth",
        str(depth),
        "--states-output",
        f"artifacts\\shards\\native_state_slice_depth{depth}.bin",
        "--states-manifest",
        f"artifacts\\shards\\native_state_slice_depth{depth}.manifest.json",
        "--edges-output",
        f"artifacts\\shards\\native_edge_slice_depth{depth}.bin",
        "--edges-manifest",
        f"artifacts\\shards\\native_edge_slice_depth{depth}.manifest.json",
        "--adjacency-output",
        f"artifacts\\shards\\native_adjacency_slice_depth{depth}.bin",
        "--adjacency-manifest",
        f"artifacts\\shards\\native_adjacency_slice_depth{depth}.manifest.json",
        "--summary-output",
        f"artifacts\\shards\\native_graph_slice_depth{depth}.summary.json",
    ]

    started = time.perf_counter()
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    elapsed_s = time.perf_counter() - started

    if completed.returncode != 0:
        if completed.stdout:
            print(completed.stdout, end="")
        if completed.stderr:
            print(completed.stderr, end="", file=sys.stderr)
        return completed.returncode

    summary_path = Path(f"artifacts/shards/native_graph_slice_depth{depth}.summary.json")
    summary = json.loads(summary_path.read_text(encoding="ascii"))
    state_path = Path(summary["states_output"])
    edge_path = Path(summary["edges_output"])
    adjacency_path = Path(summary["adjacency_output"])
    state_bytes = state_path.stat().st_size
    edge_bytes = edge_path.stat().st_size
    adjacency_bytes = adjacency_path.stat().st_size
    total_bytes = state_bytes + edge_bytes + adjacency_bytes
    internal_elapsed_seconds = summary["total_ns"] / 1_000_000_000 if summary["total_ns"] else 0.0

    benchmark = {
        "depth": depth,
        "elapsed_seconds": elapsed_s,
        "internal_elapsed_seconds": internal_elapsed_seconds,
        "process_overhead_seconds": elapsed_s - internal_elapsed_seconds,
        "state_count": summary["state_count"],
        "edge_count": summary["edge_count"],
        "state_bytes": state_bytes,
        "edge_bytes": edge_bytes,
        "adjacency_bytes": adjacency_bytes,
        "total_bytes": total_bytes,
        "states_per_second": summary["state_count"] / elapsed_s if elapsed_s else 0.0,
        "edges_per_second": summary["edge_count"] / elapsed_s if elapsed_s else 0.0,
        "bytes_per_second": total_bytes / elapsed_s if elapsed_s else 0.0,
        "internal_states_per_second": summary["state_count"] / internal_elapsed_seconds if internal_elapsed_seconds else 0.0,
        "internal_edges_per_second": summary["edge_count"] / internal_elapsed_seconds if internal_elapsed_seconds else 0.0,
        "internal_bytes_per_second": total_bytes / internal_elapsed_seconds if internal_elapsed_seconds else 0.0,
        "traversal_ns": summary["traversal_ns"],
        "sort_ns": summary["sort_ns"],
        "local_id_ns": summary["local_id_ns"],
        "state_annotation_ns": summary["state_annotation_ns"],
        "state_write_ns": summary["state_write_ns"],
        "edge_write_ns": summary["edge_write_ns"],
        "adjacency_write_ns": summary["adjacency_write_ns"],
        "total_ns_reported_by_exporter": summary["total_ns"],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(benchmark, indent=2, sort_keys=True) + "\n", encoding="ascii")
    print(f"benchmark={output}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--depth", type=int, default=6, help="Depth to export and benchmark.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/benchmarks/native_binary_export_depth6.json"),
        help="Benchmark output JSON path.",
    )
    args = parser.parse_args()
    raise SystemExit(main(args.depth, args.output))
