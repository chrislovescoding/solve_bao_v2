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
            "export_graph_slice",
            "--",
            "--depth",
            str(depth),
        ]
    )
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        if completed.stdout:
            print(completed.stdout, end="")
        if completed.stderr:
            print(completed.stderr, end="", file=sys.stderr)
        return completed.returncode

    states_output.parent.mkdir(parents=True, exist_ok=True)
    edges_output.parent.mkdir(parents=True, exist_ok=True)
    summary_output.parent.mkdir(parents=True, exist_ok=True)

    state_count = 0
    edge_count = 0
    expanded_state_count = 0
    terminal_state_count = 0
    terminal_edge_count = 0
    nonterminal_edge_count = 0

    with (
        states_output.open("w", encoding="ascii") as state_handle,
        edges_output.open("w", encoding="ascii") as edge_handle,
    ):
        for raw_line in completed.stdout.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            record = json.loads(line)
            record_type = record.get("record_type")
            if record_type == "state":
                state_handle.write(line + "\n")
                state_count += 1
                if record.get("expanded"):
                    expanded_state_count += 1
                if record.get("state_terminal_winner") is not None:
                    terminal_state_count += 1
            elif record_type == "edge":
                edge_handle.write(line + "\n")
                edge_count += 1
                if record.get("terminal_winner") is not None:
                    terminal_edge_count += 1
                else:
                    nonterminal_edge_count += 1
            else:
                raise ValueError(f"Unknown record_type in graph slice output: {record_type!r}")

    write_manifest(
        states_manifest,
        "state_shard_jsonl",
        states_output,
        state_count,
        [
            f"depth={depth}",
            "source=initial_position",
            "representation=canonical_state_jsonl",
            f"profile={'release' if release else 'debug'}",
            f"expanded_states={expanded_state_count}",
            f"terminal_states={terminal_state_count}",
        ],
    )
    write_manifest(
        edges_manifest,
        "edge_shard_jsonl",
        edges_output,
        edge_count,
        [
            f"depth={depth}",
            "source=initial_position",
            "representation=canonical_edge_jsonl",
            f"profile={'release' if release else 'debug'}",
            f"terminal_edges={terminal_edge_count}",
            f"nonterminal_edges={nonterminal_edge_count}",
        ],
    )

    summary = {
        "rulespec_version": RULESPEC_VERSION,
        "depth": depth,
        "profile": "release" if release else "debug",
        "state_count": state_count,
        "expanded_state_count": expanded_state_count,
        "terminal_state_count": terminal_state_count,
        "edge_count": edge_count,
        "terminal_edge_count": terminal_edge_count,
        "nonterminal_edge_count": nonterminal_edge_count,
        "states_output": str(states_output),
        "states_manifest": str(states_manifest),
        "edges_output": str(edges_output),
        "edges_manifest": str(edges_manifest),
    }
    summary_output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="ascii")

    print(f"states_payload={states_output}")
    print(f"states_manifest={states_manifest}")
    print(f"edges_payload={edges_output}")
    print(f"edges_manifest={edges_manifest}")
    print(f"summary={summary_output}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--depth", type=int, default=6, help="Number of ply layers to export from the initial state.")
    parser.add_argument(
        "--states-output",
        type=Path,
        default=Path("artifacts/shards/state_slice_depth6.jsonl"),
        help="Output JSONL path for state records.",
    )
    parser.add_argument(
        "--states-manifest",
        type=Path,
        default=Path("artifacts/shards/state_slice_depth6.manifest.json"),
        help="Manifest path for the state payload.",
    )
    parser.add_argument(
        "--edges-output",
        type=Path,
        default=Path("artifacts/shards/edge_slice_depth6.jsonl"),
        help="Output JSONL path for edge records.",
    )
    parser.add_argument(
        "--edges-manifest",
        type=Path,
        default=Path("artifacts/shards/edge_slice_depth6.manifest.json"),
        help="Manifest path for the edge payload.",
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=Path("artifacts/shards/graph_slice_depth6.summary.json"),
        help="Summary JSON path.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Run without --release.",
    )
    args = parser.parse_args()
    sys.exit(
        main(
            args.depth,
            args.states_output,
            args.states_manifest,
            args.edges_output,
            args.edges_manifest,
            args.summary_output,
            release=not args.debug,
        )
    )
