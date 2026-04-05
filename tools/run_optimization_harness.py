from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import statistics
import subprocess
import sys
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXPECTATIONS_PATH = ROOT / "benchmarks" / "hot_path_expectations.json"


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


def build_release_binary(bin_name: str) -> Path:
    cargo = resolve_cargo()
    command = [cargo, "build", "--quiet", "--release", "-p", "bao_solver_core", "--bin", bin_name]
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(
            f"cargo build failed for {bin_name}\nstdout:\n{completed.stdout[-4000:]}\nstderr:\n{completed.stderr[-4000:]}"
        )
    suffix = ".exe" if os.name == "nt" else ""
    return ROOT / "target" / "release" / f"{bin_name}{suffix}"


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="ascii")


def parse_time_metrics(stderr: str) -> dict[str, Any]:
    metrics: dict[str, Any] = {"max_rss_kb": None, "user_seconds": None, "sys_seconds": None}
    for line in stderr.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key == "Maximum resident set size (kbytes)":
            try:
                metrics["max_rss_kb"] = int(value)
            except ValueError:
                pass
        elif key == "User time (seconds)":
            try:
                metrics["user_seconds"] = float(value)
            except ValueError:
                pass
        elif key == "System time (seconds)":
            try:
                metrics["sys_seconds"] = float(value)
            except ValueError:
                pass
    return metrics


def run_measured(command: list[str], *, cwd: Path) -> dict[str, Any]:
    time_wrapper = Path("/usr/bin/time")
    wrapped = command
    using_time = False
    if time_wrapper.exists():
        wrapped = [str(time_wrapper), "-v", *command]
        using_time = True
    started = time.perf_counter()
    completed = subprocess.run(wrapped, cwd=cwd, capture_output=True, text=True, check=False)
    elapsed_seconds = time.perf_counter() - started
    metrics = {
        "command": command,
        "elapsed_seconds": elapsed_seconds,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "max_rss_kb": None,
        "user_seconds": None,
        "sys_seconds": None,
        "used_time_wrapper": using_time,
    }
    if using_time:
        metrics.update(parse_time_metrics(completed.stderr))
    return metrics


def compare_expected_subset(actual: dict[str, Any], expected: dict[str, Any]) -> list[str]:
    mismatches: list[str] = []
    for key, expected_value in expected.items():
        actual_value = actual.get(key)
        if actual_value != expected_value:
            mismatches.append(f"{key}: expected {expected_value!r}, got {actual_value!r}")
    return mismatches


def ensure_clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def load_expectations() -> dict[str, Any]:
    return json.loads(EXPECTATIONS_PATH.read_text(encoding="ascii"))


def export_command(binary: Path, depth: int, outdir: Path) -> tuple[list[str], dict[str, Path]]:
    shards = {
        "state_binary": outdir / f"native_state_slice_depth{depth}.bin",
        "edge_binary": outdir / f"native_edge_slice_depth{depth}.bin",
        "adjacency_binary": outdir / f"native_adjacency_slice_depth{depth}.bin",
        "summary": outdir / f"native_graph_slice_depth{depth}.summary.json",
    }
    command = [
        str(binary),
        "--depth",
        str(depth),
        "--states-output",
        str(shards["state_binary"]),
        "--edges-output",
        str(shards["edge_binary"]),
        "--adjacency-output",
        str(shards["adjacency_binary"]),
    ]
    return command, shards


def run_export_once(binary: Path, depth: int, outdir: Path) -> dict[str, Any]:
    ensure_clean_dir(outdir)
    command, paths = export_command(binary, depth, outdir)
    measured = run_measured(command, cwd=ROOT)
    if measured["returncode"] != 0:
        raise RuntimeError(
            f"export_binary_graph_slice failed\nstdout:\n{measured['stdout'][-4000:]}\nstderr:\n{measured['stderr'][-4000:]}"
        )
    summary = json.loads(measured["stdout"])
    write_json(paths["summary"], summary)
    hashes = {name: sha256_path(path) for name, path in paths.items() if name.endswith("_binary")}
    return {
        "measured": measured,
        "summary": summary,
        "paths": paths,
        "hashes": hashes,
    }


def ensure_export_fixture(binary: Path, depth: int, cache_root: Path) -> dict[str, Path]:
    fixture_dir = cache_root / f"export_depth{depth}"
    paths = {
        "state_binary": fixture_dir / f"native_state_slice_depth{depth}.bin",
        "edge_binary": fixture_dir / f"native_edge_slice_depth{depth}.bin",
        "adjacency_binary": fixture_dir / f"native_adjacency_slice_depth{depth}.bin",
        "summary": fixture_dir / f"native_graph_slice_depth{depth}.summary.json",
    }
    if all(path.exists() for path in paths.values()):
        return paths
    result = run_export_once(binary, depth, fixture_dir)
    return result["paths"]


def solve_command(
    binary: Path,
    *,
    state_binary: Path,
    adjacency_binary: Path,
    graph_summary: Path,
    outdir: Path,
    depth_label: str,
) -> dict[str, Any]:
    paths = {
        "summary": outdir / f"slice_scc_{depth_label}.json",
        "solution_binary": outdir / f"slice_scc_{depth_label}.bin",
        "analysis": outdir / f"scc_{depth_label}.json",
    }
    command = [
        str(binary),
        "--state-binary",
        str(state_binary),
        "--adjacency-binary",
        str(adjacency_binary),
        "--graph-summary",
        str(graph_summary),
        "--output",
        str(paths["summary"]),
        "--solution-output",
        str(paths["solution_binary"]),
        "--scc-summary-output",
        str(paths["analysis"]),
    ]
    return {"command": command, "paths": paths}


def run_solver_once(
    binary: Path,
    *,
    state_binary: Path,
    adjacency_binary: Path,
    graph_summary: Path,
    outdir: Path,
    depth_label: str,
) -> dict[str, Any]:
    ensure_clean_dir(outdir)
    prepared = solve_command(
        binary,
        state_binary=state_binary,
        adjacency_binary=adjacency_binary,
        graph_summary=graph_summary,
        outdir=outdir,
        depth_label=depth_label,
    )
    measured = run_measured(prepared["command"], cwd=ROOT)
    if measured["returncode"] != 0:
        raise RuntimeError(
            f"solve_slice_dag failed\nstdout:\n{measured['stdout'][-4000:]}\nstderr:\n{measured['stderr'][-4000:]}"
        )
    summary = json.loads(prepared["paths"]["summary"].read_text(encoding="ascii"))
    hashes = {"solution_binary": sha256_path(prepared["paths"]["solution_binary"])}
    return {
        "measured": measured,
        "summary": summary,
        "paths": prepared["paths"],
        "hashes": hashes,
    }


def aggregate_trials(trials: list[dict[str, Any]], *, throughput_keys: dict[str, str]) -> dict[str, Any]:
    wall_times = [trial["elapsed_seconds"] for trial in trials]
    max_rss_values = [trial["max_rss_kb"] for trial in trials if trial["max_rss_kb"] is not None]
    aggregate = {
        "trial_count": len(trials),
        "median_wall_seconds": statistics.median(wall_times),
        "min_wall_seconds": min(wall_times),
        "max_wall_seconds": max(wall_times),
        "mean_wall_seconds": statistics.fmean(wall_times),
        "median_max_rss_kb": statistics.median(max_rss_values) if max_rss_values else None,
        "min_max_rss_kb": min(max_rss_values) if max_rss_values else None,
        "max_max_rss_kb": max(max_rss_values) if max_rss_values else None,
    }
    for metric_name, source_key in throughput_keys.items():
        values = [trial[source_key] for trial in trials]
        aggregate[f"median_{metric_name}"] = statistics.median(values)
        aggregate[f"mean_{metric_name}"] = statistics.fmean(values)
    return aggregate


def harness_export(args: argparse.Namespace, expectations: dict[str, Any]) -> dict[str, Any]:
    binary = build_release_binary("export_binary_graph_slice")
    correctness_results = []
    for depth_text in args.correctness_depths.split(","):
        depth = int(depth_text)
        expected = expectations["export_binary"][str(depth)]
        result = run_export_once(binary, depth, args.work_root / "correctness" / f"depth{depth}")
        mismatches = []
        mismatches.extend(compare_expected_subset(result["summary"], expected["summary"]))
        mismatches.extend(
            f"{key}: expected {value}, got {result['hashes'].get(key)}"
            for key, value in expected["hashes"].items()
            if result["hashes"].get(key) != value
        )
        correctness_results.append(
            {
                "depth": depth,
                "passed": not mismatches,
                "mismatches": mismatches,
                "summary_subset": {key: result["summary"][key] for key in expected["summary"]},
                "hashes": result["hashes"],
            }
        )
    if any(not result["passed"] for result in correctness_results):
        raise RuntimeError("export correctness gate failed")

    trial_results = []
    for trial in range(1, args.trials + 1):
        result = run_export_once(binary, args.benchmark_depth, args.work_root / "benchmark" / f"trial_{trial}")
        summary = result["summary"]
        measured = result["measured"]
        trial_results.append(
            {
                "trial": trial,
                "elapsed_seconds": measured["elapsed_seconds"],
                "max_rss_kb": measured["max_rss_kb"],
                "user_seconds": measured["user_seconds"],
                "sys_seconds": measured["sys_seconds"],
                "state_count": summary["state_count"],
                "edge_count": summary["edge_count"],
                "states_per_second": summary["state_count"] / measured["elapsed_seconds"],
                "edges_per_second": summary["edge_count"] / measured["elapsed_seconds"],
                "exporter_total_seconds": summary["total_ns"] / 1_000_000_000,
                "traversal_seconds": summary["traversal_ns"] / 1_000_000_000,
                "sort_seconds": summary["sort_ns"] / 1_000_000_000,
                "annotation_seconds": summary["state_annotation_ns"] / 1_000_000_000,
                "write_seconds": (
                    summary["state_write_ns"] + summary["edge_write_ns"] + summary["adjacency_write_ns"]
                )
                / 1_000_000_000,
            }
        )
    return {
        "target": "export_binary",
        "binary": str(binary),
        "benchmark_depth": args.benchmark_depth,
        "correctness": correctness_results,
        "performance_trials": trial_results,
        "performance_aggregate": aggregate_trials(
            trial_results,
            throughput_keys={"states_per_second": "states_per_second", "edges_per_second": "edges_per_second"},
        ),
    }


def harness_solve(args: argparse.Namespace, expectations: dict[str, Any]) -> dict[str, Any]:
    export_binary = build_release_binary("export_binary_graph_slice")
    solve_binary = build_release_binary("solve_slice_dag")
    fixture_root = args.work_root / "fixtures"

    correctness_results = []
    for depth_text in args.correctness_depths.split(","):
        depth = int(depth_text)
        fixture = ensure_export_fixture(export_binary, depth, fixture_root)
        expected = expectations["solve_slice_dag"][str(depth)]
        result = run_solver_once(
            solve_binary,
            state_binary=fixture["state_binary"],
            adjacency_binary=fixture["adjacency_binary"],
            graph_summary=fixture["summary"],
            outdir=args.work_root / "correctness" / f"depth{depth}",
            depth_label=f"depth{depth}",
        )
        mismatches = []
        mismatches.extend(compare_expected_subset(result["summary"], expected["summary"]))
        mismatches.extend(
            f"{key}: expected {value}, got {result['hashes'].get(key)}"
            for key, value in expected["hashes"].items()
            if result["hashes"].get(key) != value
        )
        correctness_results.append(
            {
                "depth": depth,
                "passed": not mismatches,
                "mismatches": mismatches,
                "summary_subset": {key: result["summary"][key] for key in expected["summary"]},
                "hashes": result["hashes"],
            }
        )
    if any(not result["passed"] for result in correctness_results):
        raise RuntimeError("solve_slice_dag correctness gate failed")

    if args.benchmark_state_binary:
        benchmark_inputs = {
            "state_binary": args.benchmark_state_binary,
            "adjacency_binary": args.benchmark_adjacency_binary,
            "summary": args.benchmark_graph_summary,
        }
    else:
        benchmark_inputs = ensure_export_fixture(export_binary, args.benchmark_depth, fixture_root)

    trial_results = []
    for trial in range(1, args.trials + 1):
        result = run_solver_once(
            solve_binary,
            state_binary=benchmark_inputs["state_binary"],
            adjacency_binary=benchmark_inputs["adjacency_binary"],
            graph_summary=benchmark_inputs["summary"],
            outdir=args.work_root / "benchmark" / f"trial_{trial}",
            depth_label=f"benchmark_depth{args.benchmark_depth}",
        )
        summary = result["summary"]
        measured = result["measured"]
        trial_results.append(
            {
                "trial": trial,
                "elapsed_seconds": measured["elapsed_seconds"],
                "max_rss_kb": measured["max_rss_kb"],
                "user_seconds": measured["user_seconds"],
                "sys_seconds": measured["sys_seconds"],
                "expanded_state_count": summary["expanded_state_count"],
                "resolved_state_count": summary["resolved_state_count"],
                "expanded_states_per_second": summary["expanded_state_count"] / measured["elapsed_seconds"],
                "resolved_states_per_second": summary["resolved_state_count"] / measured["elapsed_seconds"],
                "root_status": summary["root_status"],
            }
        )
    return {
        "target": "solve_slice_dag",
        "binary": str(solve_binary),
        "benchmark_depth": args.benchmark_depth,
        "benchmark_inputs": {key: str(value) for key, value in benchmark_inputs.items()},
        "correctness": correctness_results,
        "performance_trials": trial_results,
        "performance_aggregate": aggregate_trials(
            trial_results,
            throughput_keys={
                "expanded_states_per_second": "expanded_states_per_second",
                "resolved_states_per_second": "resolved_states_per_second",
            },
        ),
    }


def run_python_check(command: list[str]) -> dict[str, Any]:
    measured = run_measured(command, cwd=ROOT)
    return {
        "command": command,
        "returncode": measured["returncode"],
        "elapsed_seconds": measured["elapsed_seconds"],
        "stdout_tail": measured["stdout"][-2000:],
        "stderr_tail": measured["stderr"][-2000:],
    }


def harness_statekey(args: argparse.Namespace, expectations: dict[str, Any]) -> dict[str, Any]:
    binary = build_release_binary("bench_statekey")
    checker = ROOT / "tools" / "check_native_statekeys.py"
    correctness_results = []
    for corpus in args.correctness_corpora:
        command = [sys.executable, str(checker), str(corpus)]
        result = run_python_check(command)
        correctness_results.append(
            {
                "corpus": str(corpus),
                "passed": result["returncode"] == 0,
                "elapsed_seconds": result["elapsed_seconds"],
                "stdout_tail": result["stdout_tail"],
                "stderr_tail": result["stderr_tail"],
            }
        )
    if any(not result["passed"] for result in correctness_results):
        raise RuntimeError("statekey correctness gate failed")

    expected_benchmark = expectations["statekey"]["benchmark"]
    if str(args.benchmark_corpus).replace("\\", "/") != expected_benchmark["corpus"]:
        raise RuntimeError("statekey benchmark corpus does not match pinned expectation corpus")

    trial_results = []
    for trial in range(1, args.trials + 1):
        command = [
            str(binary),
            "--corpus",
            str(args.benchmark_corpus),
            "--warmup-iterations",
            str(args.warmup_iterations),
            "--iterations",
            str(args.iterations),
        ]
        measured = run_measured(command, cwd=ROOT)
        if measured["returncode"] != 0:
            raise RuntimeError(
                f"bench_statekey failed\nstdout:\n{measured['stdout'][-4000:]}\nstderr:\n{measured['stderr'][-4000:]}"
            )
        report = json.loads(measured["stdout"])
        pack_checksum = report["pack_key"]["checksum_hex"]
        unpack_checksum = report["unpack_key"]["checksum_hex"]
        if pack_checksum != expected_benchmark["pack_key_checksum_hex"]:
            raise RuntimeError("statekey pack_key checksum gate failed")
        if unpack_checksum != expected_benchmark["unpack_key_checksum_hex"]:
            raise RuntimeError("statekey unpack_key checksum gate failed")
        trial_results.append(
            {
                "trial": trial,
                "elapsed_seconds": measured["elapsed_seconds"],
                "max_rss_kb": measured["max_rss_kb"],
                "user_seconds": measured["user_seconds"],
                "sys_seconds": measured["sys_seconds"],
                "pack_ns_per_op": report["pack_key"]["ns_per_op"],
                "pack_ops_per_sec": report["pack_key"]["ops_per_sec"],
                "unpack_ns_per_op": report["unpack_key"]["ns_per_op"],
                "unpack_ops_per_sec": report["unpack_key"]["ops_per_sec"],
                "records": report["records"],
            }
        )
    return {
        "target": "statekey",
        "binary": str(binary),
        "benchmark_corpus": str(args.benchmark_corpus),
        "correctness": correctness_results,
        "performance_trials": trial_results,
        "performance_aggregate": aggregate_trials(
            trial_results,
            throughput_keys={"pack_ops_per_sec": "pack_ops_per_sec", "unpack_ops_per_sec": "unpack_ops_per_sec"},
        ),
    }


def harness_movegen(args: argparse.Namespace, expectations: dict[str, Any]) -> dict[str, Any]:
    binary = build_release_binary("bench_movegen")
    legal_checker = ROOT / "tools" / "check_native_legal_moves.py"
    successor_checker = ROOT / "tools" / "check_native_successors.py"
    correctness_results = []
    for corpus in args.correctness_corpora:
        for label, checker in (("legal_moves", legal_checker), ("successors", successor_checker)):
            command = [sys.executable, str(checker), str(corpus)]
            result = run_python_check(command)
            correctness_results.append(
                {
                    "corpus": str(corpus),
                    "check": label,
                    "passed": result["returncode"] == 0,
                    "elapsed_seconds": result["elapsed_seconds"],
                    "stdout_tail": result["stdout_tail"],
                    "stderr_tail": result["stderr_tail"],
                }
            )
    if any(not result["passed"] for result in correctness_results):
        raise RuntimeError("movegen correctness gate failed")

    expected_benchmark = expectations["movegen"]["benchmark"]
    if str(args.benchmark_corpus).replace("\\", "/") != expected_benchmark["corpus"]:
        raise RuntimeError("movegen benchmark corpus does not match pinned expectation corpus")

    trial_results = []
    for trial in range(1, args.trials + 1):
        command = [
            str(binary),
            "--corpus",
            str(args.benchmark_corpus),
            "--warmup-iterations",
            str(args.warmup_iterations),
            "--iterations",
            str(args.iterations),
        ]
        measured = run_measured(command, cwd=ROOT)
        if measured["returncode"] != 0:
            raise RuntimeError(
                f"bench_movegen failed\nstdout:\n{measured['stdout'][-4000:]}\nstderr:\n{measured['stderr'][-4000:]}"
            )
        report = json.loads(measured["stdout"])
        if report["legal_moves"]["checksum_hex"] != expected_benchmark["legal_moves_checksum_hex"]:
            raise RuntimeError("movegen legal_moves checksum gate failed")
        if report["apply_move"]["checksum_hex"] != expected_benchmark["apply_move_checksum_hex"]:
            raise RuntimeError("movegen apply_move checksum gate failed")
        trial_results.append(
            {
                "trial": trial,
                "elapsed_seconds": measured["elapsed_seconds"],
                "max_rss_kb": measured["max_rss_kb"],
                "user_seconds": measured["user_seconds"],
                "sys_seconds": measured["sys_seconds"],
                "legal_moves_ns_per_op": report["legal_moves"]["ns_per_op"],
                "legal_moves_ops_per_sec": report["legal_moves"]["ops_per_sec"],
                "apply_move_ns_per_op": report["apply_move"]["ns_per_op"],
                "apply_move_ops_per_sec": report["apply_move"]["ops_per_sec"],
                "states": report["states"],
                "legal_move_pairs": report["legal_move_pairs"],
            }
        )
    return {
        "target": "movegen",
        "binary": str(binary),
        "benchmark_corpus": str(args.benchmark_corpus),
        "correctness": correctness_results,
        "performance_trials": trial_results,
        "performance_aggregate": aggregate_trials(
            trial_results,
            throughput_keys={
                "legal_moves_ops_per_sec": "legal_moves_ops_per_sec",
                "apply_move_ops_per_sec": "apply_move_ops_per_sec",
            },
        ),
    }


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--correctness-depths", default="6,9", help="Comma-separated deterministic correctness depths.")
    parser.add_argument("--benchmark-depth", type=int, default=9, help="Depth used for the performance benchmark.")
    parser.add_argument("--trials", type=int, default=3, help="Number of measured benchmark trials.")
    parser.add_argument(
        "--work-root",
        type=Path,
        default=Path("artifacts/benchmarks/optimization_work"),
        help="Scratch directory for generated benchmark artifacts.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Report JSON output path. Defaults to artifacts/benchmarks/<target>_depth<benchmark-depth>.json",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="target", required=True)

    export_parser = subparsers.add_parser("export_binary", help="Correctness+performance harness for export_binary_graph_slice.")
    add_common_arguments(export_parser)

    solve_parser = subparsers.add_parser("solve_slice_dag", help="Correctness+performance harness for solve_slice_dag.")
    add_common_arguments(solve_parser)
    solve_parser.add_argument("--benchmark-state-binary", type=Path, default=None, help="Optional prebuilt benchmark state shard.")
    solve_parser.add_argument("--benchmark-adjacency-binary", type=Path, default=None, help="Optional prebuilt benchmark adjacency shard.")
    solve_parser.add_argument("--benchmark-graph-summary", type=Path, default=None, help="Optional graph summary for prebuilt benchmark shards.")

    statekey_parser = subparsers.add_parser("statekey", help="Correctness+performance harness for state packing kernels.")
    statekey_parser.add_argument(
        "--correctness-corpora",
        type=lambda value: [Path(item) for item in value.split(",") if item],
        default=[Path("artifacts/reference_corpus_depth2.jsonl"), Path("artifacts/reference_corpus_depth3.jsonl")],
        help="Comma-separated corpus paths for deterministic statekey checks.",
    )
    statekey_parser.add_argument(
        "--benchmark-corpus",
        type=Path,
        default=Path("artifacts/reference_corpus_depth2.jsonl"),
        help="Corpus path for statekey benchmarking.",
    )
    statekey_parser.add_argument("--warmup-iterations", type=int, default=2_000, help="Warmup loop count.")
    statekey_parser.add_argument("--iterations", type=int, default=200_000, help="Measured loop count.")
    statekey_parser.add_argument("--trials", type=int, default=3, help="Number of measured benchmark trials.")
    statekey_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Report JSON output path. Defaults to artifacts/benchmarks/statekey.json",
    )

    movegen_parser = subparsers.add_parser("movegen", help="Correctness+performance harness for move-generation kernels.")
    movegen_parser.add_argument(
        "--correctness-corpora",
        type=lambda value: [Path(item) for item in value.split(",") if item],
        default=[Path("artifacts/reference_corpus_depth2.jsonl"), Path("artifacts/reference_corpus_depth3.jsonl")],
        help="Comma-separated corpus paths for deterministic movegen checks.",
    )
    movegen_parser.add_argument(
        "--benchmark-corpus",
        type=Path,
        default=Path("artifacts/reference_corpus_depth3.jsonl"),
        help="Corpus path for movegen benchmarking.",
    )
    movegen_parser.add_argument("--warmup-iterations", type=int, default=500, help="Warmup loop count.")
    movegen_parser.add_argument("--iterations", type=int, default=20_000, help="Measured loop count.")
    movegen_parser.add_argument("--trials", type=int, default=3, help="Number of measured benchmark trials.")
    movegen_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Report JSON output path. Defaults to artifacts/benchmarks/movegen.json",
    )

    args = parser.parse_args(argv)
    expectations = load_expectations()
    if args.target == "solve_slice_dag":
        if any(value is not None for value in (args.benchmark_state_binary, args.benchmark_adjacency_binary, args.benchmark_graph_summary)):
            if not all(value is not None for value in (args.benchmark_state_binary, args.benchmark_adjacency_binary, args.benchmark_graph_summary)):
                raise SystemExit("benchmark-state-binary, benchmark-adjacency-binary, and benchmark-graph-summary must be provided together")

    if args.target == "export_binary":
        report = harness_export(args, expectations)
    elif args.target == "solve_slice_dag":
        report = harness_solve(args, expectations)
    elif args.target == "statekey":
        report = harness_statekey(args, expectations)
    else:
        report = harness_movegen(args, expectations)

    report.update(
        {
            "host": platform.node(),
            "platform": platform.platform(),
            "python_version": sys.version.split()[0],
            "cpu_count": os.cpu_count(),
            "promotion_rule": {
                "stage_speedup_required": 0.2,
                "end_to_end_speedup_required": 0.1,
                "correctness_must_pass": True,
                "deterministic_outputs_required": True,
            },
        }
    )
    if args.output is None:
        if hasattr(args, "benchmark_depth"):
            args.output = Path("artifacts/benchmarks") / f"{args.target}_depth{args.benchmark_depth}.json"
        else:
            args.output = Path("artifacts/benchmarks") / f"{args.target}.json"
    write_json(args.output, report)
    print(f"benchmark_report={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
