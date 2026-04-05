from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
RULESPEC_VERSION = "rulespec-v1.0.0-draft"


def resolve_python() -> str:
    return sys.executable


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


def run_step(name: str, command: list[str], *, cwd: Path, skip_if_exists: Path | None = None) -> dict[str, object]:
    if skip_if_exists is not None and skip_if_exists.exists():
        return {
            "name": name,
            "status": "skipped",
            "reason": f"exists:{skip_if_exists}",
            "command": command,
            "elapsed_seconds": 0.0,
        }

    started = time.perf_counter()
    completed = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)
    elapsed = time.perf_counter() - started
    step = {
        "name": name,
        "status": "ok" if completed.returncode == 0 else "failed",
        "returncode": completed.returncode,
        "command": command,
        "elapsed_seconds": elapsed,
        "stdout_tail": completed.stdout[-4000:],
        "stderr_tail": completed.stderr[-4000:],
    }
    if completed.returncode != 0:
        raise RuntimeError(json.dumps(step, indent=2))
    return step


def main(
    depth: int,
    output_dir: Path,
    include_jsonl: bool,
    include_census: bool,
    release: bool,
    resume: bool,
) -> int:
    python = resolve_python()
    _cargo = resolve_cargo()
    output_dir.mkdir(parents=True, exist_ok=True)
    shards_dir = output_dir / "shards"
    solve_dir = output_dir / "solve"
    analysis_dir = output_dir / "analysis"
    census_dir = output_dir / "census"
    for directory in (shards_dir, solve_dir, analysis_dir, census_dir):
        directory.mkdir(parents=True, exist_ok=True)

    state_bin = shards_dir / f"native_state_slice_depth{depth}.bin"
    edge_bin = shards_dir / f"native_edge_slice_depth{depth}.bin"
    adjacency_bin = shards_dir / f"native_adjacency_slice_depth{depth}.bin"
    binary_summary = shards_dir / f"native_graph_slice_depth{depth}.summary.json"
    state_jsonl = shards_dir / f"state_slice_depth{depth}.jsonl"
    edge_jsonl = shards_dir / f"edge_slice_depth{depth}.jsonl"
    json_summary = shards_dir / f"graph_slice_depth{depth}.summary.json"
    solve_summary = solve_dir / f"slice_scc_depth{depth}.json"
    solve_bin = solve_dir / f"slice_scc_depth{depth}.bin"
    solve_manifest = solve_dir / f"slice_scc_depth{depth}.manifest.json"
    scc_summary = analysis_dir / f"scc_depth{depth}.json"
    census_output = census_dir / f"shallow_depth{depth}_{'release' if release else 'debug'}.json"

    steps: list[dict[str, object]] = []
    debug_flag = [] if release else ["--debug"]

    if include_census:
        steps.append(
            run_step(
                "census",
                [
                    python,
                    "tools/run_native_shallow_census.py",
                    "--depth",
                    str(depth),
                    "--output",
                    str(census_output),
                    *debug_flag,
                ],
                cwd=ROOT,
                skip_if_exists=census_output if resume else None,
            )
        )

    if include_jsonl:
        steps.append(
            run_step(
                "export_jsonl",
                [
                    python,
                    "tools/export_native_graph_slice.py",
                    "--depth",
                    str(depth),
                    "--states-output",
                    str(state_jsonl),
                    "--states-manifest",
                    str(shards_dir / f"state_slice_depth{depth}.manifest.json"),
                    "--edges-output",
                    str(edge_jsonl),
                    "--edges-manifest",
                    str(shards_dir / f"edge_slice_depth{depth}.manifest.json"),
                    "--summary-output",
                    str(json_summary),
                    *debug_flag,
                ],
                cwd=ROOT,
                skip_if_exists=json_summary if resume else None,
            )
        )

    steps.append(
        run_step(
            "export_binary",
            [
                python,
                "tools/export_native_binary_graph_slice.py",
                "--depth",
                str(depth),
                "--states-output",
                str(state_bin),
                "--states-manifest",
                str(shards_dir / f"native_state_slice_depth{depth}.manifest.json"),
                "--edges-output",
                str(edge_bin),
                "--edges-manifest",
                str(shards_dir / f"native_edge_slice_depth{depth}.manifest.json"),
                "--adjacency-output",
                str(adjacency_bin),
                "--adjacency-manifest",
                str(shards_dir / f"native_adjacency_slice_depth{depth}.manifest.json"),
                "--summary-output",
                str(binary_summary),
                *debug_flag,
            ],
            cwd=ROOT,
            skip_if_exists=binary_summary if resume else None,
        )
    )

    if include_jsonl:
        steps.append(
            run_step(
                "verify_binary",
                [
                    python,
                    "tools/verify_native_binary_graph_slice.py",
                    "--state-jsonl",
                    str(state_jsonl),
                    "--state-binary",
                    str(state_bin),
                    "--edge-jsonl",
                    str(edge_jsonl),
                    "--edge-binary",
                    str(edge_bin),
                ],
                cwd=ROOT,
            )
        )
        steps.append(
            run_step(
                "verify_adjacency",
                [
                    python,
                    "tools/verify_native_adjacency_graph_slice.py",
                    "--state-jsonl",
                    str(state_jsonl),
                    "--edge-jsonl",
                    str(edge_jsonl),
                    "--adjacency-binary",
                    str(adjacency_bin),
                ],
                cwd=ROOT,
            )
        )

    steps.append(
        run_step(
            "solve_scc",
            [
                python,
                "tools/solve_slice_scc.py",
                "--state-binary",
                str(state_bin),
                "--adjacency-binary",
                str(adjacency_bin),
                "--graph-summary",
                str(binary_summary),
                "--output",
                str(solve_summary),
                "--solution-output",
                str(solve_bin),
                "--solution-manifest",
                str(solve_manifest),
                "--scc-summary-output",
                str(scc_summary),
            ],
            cwd=ROOT,
            skip_if_exists=solve_summary if resume else None,
        )
    )

    steps.append(
        run_step(
            "verify_solution",
            [
                python,
                "tools/verify_partial_solution_shard.py",
                "--state-binary",
                str(state_bin),
                "--solution-binary",
                str(solve_bin),
                "--summary-json",
                str(solve_summary),
            ],
            cwd=ROOT,
        )
    )

    job_summary = {
        "rulespec_version": RULESPEC_VERSION,
        "depth": depth,
        "release": release,
        "include_jsonl": include_jsonl,
        "include_census": include_census,
        "resume": resume,
        "steps": steps,
        "artifacts": {
            "state_binary": str(state_bin),
            "edge_binary": str(edge_bin),
            "adjacency_binary": str(adjacency_bin),
            "binary_summary": str(binary_summary),
            "solve_summary": str(solve_summary),
            "solve_binary": str(solve_bin),
            "solve_manifest": str(solve_manifest),
            "scc_summary": str(scc_summary),
            "state_jsonl": str(state_jsonl) if include_jsonl else None,
            "edge_jsonl": str(edge_jsonl) if include_jsonl else None,
            "json_summary": str(json_summary) if include_jsonl else None,
            "census_output": str(census_output) if include_census else None,
        },
    }
    manifest_path = output_dir / f"pipeline_depth{depth}.manifest.json"
    manifest_path.write_text(json.dumps(job_summary, indent=2, sort_keys=True) + "\n", encoding="ascii")
    print(f"pipeline_manifest={manifest_path}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--depth", type=int, required=True, help="Depth limit for the slice job.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/pipeline"),
        help="Directory where the depth-specific pipeline outputs should be written.",
    )
    parser.add_argument(
        "--skip-jsonl",
        action="store_true",
        help="Skip JSONL export and binary-vs-JSONL verification to save time and disk.",
    )
    parser.add_argument(
        "--skip-census",
        action="store_true",
        help="Skip the shallow census stage.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Run the native tools without --release.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Reuse existing stage outputs when present.",
    )
    args = parser.parse_args()
    raise SystemExit(
        main(
            depth=args.depth,
            output_dir=args.output_dir,
            include_jsonl=not args.skip_jsonl,
            include_census=not args.skip_census,
            release=not args.debug,
            resume=args.resume,
        )
    )
