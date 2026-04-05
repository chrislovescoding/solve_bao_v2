from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from bao.reference import Direction, GameState, Move, Player, legal_moves


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


def parse_player(name: str) -> Player:
    if name == "south":
        return Player.SOUTH
    if name == "north":
        return Player.NORTH
    raise ValueError(f"Unknown player name: {name}")


def encode_move(move: Move) -> int:
    direction_bit = 0 if move.direction is Direction.CLOCKWISE else 1
    return (move.start << 1) | direction_bit


def expected_moves_by_line(corpus: Path) -> dict[int, list[int]]:
    results: dict[int, list[int]] = {}
    with corpus.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            state = GameState(tuple(record["state"]), parse_player(record["to_move"]))
            results[line_number] = sorted(encode_move(move) for move in legal_moves(state))
    return results


def actual_moves_by_line(corpus: Path) -> dict[int, list[int]]:
    cargo = resolve_cargo()
    command = [
        cargo,
        "run",
        "--quiet",
        "-p",
        "bao_solver_core",
        "--bin",
        "legal_moves_corpus",
        "--",
        str(corpus),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        if completed.stdout:
            print(completed.stdout, end="")
        if completed.stderr:
            print(completed.stderr, end="", file=sys.stderr)
        raise RuntimeError(f"native legal-move check failed with exit code {completed.returncode}")

    results: dict[int, list[int]] = {}
    for line in completed.stdout.splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        results[int(record["line_number"])] = list(record["legal_moves"])
    return results


def main(corpus: Path) -> int:
    expected = expected_moves_by_line(corpus)
    actual = actual_moves_by_line(corpus)

    if expected.keys() != actual.keys():
        missing_expected = sorted(actual.keys() - expected.keys())
        missing_actual = sorted(expected.keys() - actual.keys())
        raise AssertionError(
            f"Mismatched line coverage. extra_native={missing_expected} missing_native={missing_actual}"
        )

    for line_number in sorted(expected):
        if expected[line_number] != actual[line_number]:
            raise AssertionError(
                f"Line {line_number} mismatch. expected={expected[line_number]} actual={actual[line_number]}"
            )

    print(f"validated_records={len(expected)}")
    print(f"corpus_path={corpus}")
    return 0


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
