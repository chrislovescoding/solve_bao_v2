from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


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


def write_manifest(path: Path, payload_path: Path, item_count: int, resolved_count: int, depth: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "artifact_type": "solution_shard_binary_v1_scc_slice",
        "rulespec_version": "rulespec-v1.0.0-draft",
        "code_revision": "workspace-unversioned",
        "item_count": item_count,
        "payload_bytes": payload_path.stat().st_size,
        "sha256": sha256_path(payload_path),
        "notes": [
            f"depth={depth}",
            "source=native_dag_slice_solver_or_python_fallback",
            "representation=local_id_aligned_solution_records",
            "record_size=8",
            f"resolved_records={resolved_count}",
        ],
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="ascii")


def run(command: list[str]) -> int:
    completed = subprocess.run(command, cwd=ROOT, check=False)
    return int(completed.returncode)


def main(
    state_binary: Path,
    adjacency_binary: Path,
    graph_summary: Path,
    output: Path,
    solution_output: Path,
    solution_manifest: Path,
    scc_summary_output: Path,
) -> int:
    cargo = resolve_cargo()
    native_command = [
        cargo,
        "run",
        "--quiet",
        "--release",
        "-p",
        "bao_solver_core",
        "--bin",
        "solve_slice_dag",
        "--",
        "--state-binary",
        str(state_binary),
        "--adjacency-binary",
        str(adjacency_binary),
        "--graph-summary",
        str(graph_summary),
        "--output",
        str(output),
        "--solution-output",
        str(solution_output),
        "--solution-manifest",
        str(solution_manifest),
        "--scc-summary-output",
        str(scc_summary_output),
    ]
    print("[solve_slice_scc_native] trying_native_dag_solver", flush=True)
    native_returncode = run(native_command)
    if native_returncode == 0:
        summary = json.loads(output.read_text(encoding="ascii"))
        write_manifest(
            solution_manifest,
            solution_output,
            item_count=int(summary["state_count"]),
            resolved_count=int(summary["resolved_state_count"]),
            depth=int(summary["depth"]),
        )
        print("[solve_slice_scc_native] native_dag_solver_succeeded", flush=True)
        print(f"solution_manifest={solution_manifest}")
        return 0
    if native_returncode != 3:
        return native_returncode

    print("[solve_slice_scc_native] cycle_detected_falling_back_to_python", flush=True)
    python_command = [
        sys.executable,
        "-u",
        "tools/solve_slice_scc.py",
        "--state-binary",
        str(state_binary),
        "--adjacency-binary",
        str(adjacency_binary),
        "--graph-summary",
        str(graph_summary),
        "--output",
        str(output),
        "--solution-output",
        str(solution_output),
        "--solution-manifest",
        str(solution_manifest),
        "--scc-summary-output",
        str(scc_summary_output),
    ]
    return run(python_command)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-binary", type=Path, required=True)
    parser.add_argument("--adjacency-binary", type=Path, required=True)
    parser.add_argument("--graph-summary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--solution-output", type=Path, required=True)
    parser.add_argument("--solution-manifest", type=Path, required=True)
    parser.add_argument("--scc-summary-output", type=Path, required=True)
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
