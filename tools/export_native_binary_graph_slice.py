from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys


RULESPEC_VERSION = "rulespec-v1.0.0-draft"


def resolve_cargo() -> str:
    cargo = shutil.which("cargo")
    if cargo:
        return cargo

    home = Path.home()
    candidates = [
        home / ".cargo" / "bin" / "cargo.exe",
        home / ".cargo" / "bin" / "cargo",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    raise FileNotFoundError("Could not locate cargo on PATH or under ~/.cargo/bin.")


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


def main(
    depth: int,
    states_output: Path,
    states_manifest: Path,
    edges_output: Path,
    edges_manifest: Path,
    adjacency_output: Path,
    adjacency_manifest: Path,
    summary_output: Path,
    release: bool,
) -> int:
    cargo = resolve_cargo()
    command = [cargo, "run", "--quiet"]
    if release:
        command.append("--release")
    command.extend(
        [
            "-p",
            "bao_solver_core",
            "--bin",
            "export_binary_graph_slice",
            "--",
            "--depth",
            str(depth),
            "--states-output",
            str(states_output),
            "--edges-output",
            str(edges_output),
            "--adjacency-output",
            str(adjacency_output),
        ]
    )
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        if completed.stdout:
            print(completed.stdout, end="")
        if completed.stderr:
            print(completed.stderr, end="", file=sys.stderr)
        return completed.returncode

    summary = json.loads(completed.stdout)
    summary_output.parent.mkdir(parents=True, exist_ok=True)
    summary_output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="ascii")

    write_manifest(
        states_manifest,
        "native_state_shard_binary_v1",
        states_output,
        int(summary["state_count"]),
        [
            f"depth={depth}",
            "source=initial_position",
            "writer=native_rust",
            f"profile={'release' if release else 'debug'}",
            f"sorted_by={summary['sorted_by']}",
            f"header_bytes={summary['header_bytes']}",
            f"record_size={summary['state_record_bytes']}",
            f"expanded_states={summary['expanded_state_count']}",
            f"root_local_id={summary['root_local_id']}",
            f"root_state_key_hex={summary['root_state_key_hex']}",
        ],
    )
    write_manifest(
        edges_manifest,
        "native_edge_shard_binary_v1",
        edges_output,
        int(summary["edge_count"]),
        [
            f"depth={depth}",
            "source=initial_position",
            "writer=native_rust",
            f"profile={'release' if release else 'debug'}",
            f"sorted_by={summary['sorted_by']}",
            f"header_bytes={summary['header_bytes']}",
            f"record_size={summary['edge_record_bytes']}",
            f"terminal_edges={summary['terminal_edge_count']}",
        ],
    )
    write_manifest(
        adjacency_manifest,
        "native_adjacency_shard_binary_v1",
        adjacency_output,
        int(summary["edge_count"]),
        [
            f"depth={depth}",
            "source=initial_position",
            "writer=native_rust",
            f"profile={'release' if release else 'debug'}",
            f"sorted_by={summary['sorted_by']}",
            f"header_bytes={summary['header_bytes']}",
            f"edge_record_size={summary['adjacency_edge_record_bytes']}",
            f"offset_record_size={summary['adjacency_offset_record_bytes']}",
            f"state_count={summary['state_count']}",
            f"root_local_id={summary['root_local_id']}",
        ],
    )

    print(f"states_output={states_output}")
    print(f"states_manifest={states_manifest}")
    print(f"edges_output={edges_output}")
    print(f"edges_manifest={edges_manifest}")
    print(f"adjacency_output={adjacency_output}")
    print(f"adjacency_manifest={adjacency_manifest}")
    print(f"summary={summary_output}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--depth", type=int, default=6, help="Number of ply layers to export from the initial state.")
    parser.add_argument(
        "--states-output",
        type=Path,
        default=Path("artifacts/shards/native_state_slice_depth6.bin"),
        help="Native binary state shard output path.",
    )
    parser.add_argument(
        "--states-manifest",
        type=Path,
        default=Path("artifacts/shards/native_state_slice_depth6.manifest.json"),
        help="Manifest path for the native binary state shard.",
    )
    parser.add_argument(
        "--edges-output",
        type=Path,
        default=Path("artifacts/shards/native_edge_slice_depth6.bin"),
        help="Native binary edge shard output path.",
    )
    parser.add_argument(
        "--edges-manifest",
        type=Path,
        default=Path("artifacts/shards/native_edge_slice_depth6.manifest.json"),
        help="Manifest path for the native binary edge shard.",
    )
    parser.add_argument(
        "--adjacency-output",
        type=Path,
        default=Path("artifacts/shards/native_adjacency_slice_depth6.bin"),
        help="Native binary adjacency shard output path.",
    )
    parser.add_argument(
        "--adjacency-manifest",
        type=Path,
        default=Path("artifacts/shards/native_adjacency_slice_depth6.manifest.json"),
        help="Manifest path for the native adjacency shard.",
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=Path("artifacts/shards/native_graph_slice_depth6.summary.json"),
        help="Summary JSON path for the native binary export.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Run without --release.",
    )
    args = parser.parse_args()
    raise SystemExit(
        main(
            args.depth,
            args.states_output,
            args.states_manifest,
            args.edges_output,
            args.edges_manifest,
            args.adjacency_output,
            args.adjacency_manifest,
            args.summary_output,
            release=not args.debug,
        )
    )
