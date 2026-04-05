from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys


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


def main(corpus: Path, output: Path, warmup_iterations: int, iterations: int) -> int:
    cargo = resolve_cargo()
    command = [
        cargo,
        "run",
        "--quiet",
        "--release",
        "-p",
        "bao_solver_core",
        "--bin",
        "bench_statekey",
        "--",
        "--corpus",
        str(corpus),
        "--warmup-iterations",
        str(warmup_iterations),
        "--iterations",
        str(iterations),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        if completed.stdout:
            print(completed.stdout, end="")
        if completed.stderr:
            print(completed.stderr, end="", file=sys.stderr)
        return completed.returncode

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(completed.stdout, encoding="ascii")
    print(f"benchmark_report={output}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--corpus",
        type=Path,
        default=Path("artifacts/reference_corpus_depth2.jsonl"),
        help="Reference corpus JSONL path.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/benchmarks/statekey_benchmark_release.json"),
        help="Output JSON path.",
    )
    parser.add_argument(
        "--warmup-iterations",
        type=int,
        default=2_000,
        help="Warmup loop count for each kernel.",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=200_000,
        help="Measured loop count for each kernel.",
    )
    args = parser.parse_args()
    sys.exit(main(args.corpus, args.output, args.warmup_iterations, args.iterations))
