from __future__ import annotations

import argparse
import os
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


def main(corpus: Path) -> int:
    cargo = resolve_cargo()
    command = [
        cargo,
        "run",
        "--quiet",
        "-p",
        "bao_solver_core",
        "--bin",
        "statekey_corpus",
        "--",
        str(corpus),
    ]
    completed = subprocess.run(command, check=False)
    return completed.returncode


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "corpus",
        nargs="?",
        type=Path,
        default=Path("artifacts/reference_corpus_depth2.jsonl"),
        help="Reference corpus JSONL path.",
    )
    args = parser.parse_args()
    sys.exit(main(args.corpus))
