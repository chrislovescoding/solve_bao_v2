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


def main(depth: int, output: Path, release: bool) -> int:
    cargo = resolve_cargo()
    command = [cargo, "run", "--quiet"]
    if release:
        command.append("--release")
    command.extend(
        [
            "-p",
            "bao_solver_core",
            "--bin",
            "shallow_census",
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

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(completed.stdout, encoding="ascii")
    print(f"census_report={output}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--depth", type=int, default=6, help="Number of ply layers to profile from the initial state.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/census/shallow_depth6_release.json"),
        help="Output JSON path.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Run without --release.",
    )
    args = parser.parse_args()
    sys.exit(main(args.depth, args.output, release=not args.debug))
