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

from bao.packing import canonical_state_key_hex
from bao.reference import Direction, GameState, Move, MoveResult, Player, apply_move, legal_moves


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


def player_name(player: Player | None) -> str | None:
    if player is None:
        return None
    return "south" if player is Player.SOUTH else "north"


def result_summary(move: Move, result: MoveResult) -> dict[str, object]:
    return {
        "move_code": encode_move(move),
        "move_kind": result.move_kind.value,
        "sowings": result.sowings,
        "seeds_sown": result.seeds_sown,
        "captures": sum(1 for event in result.trace if event.capture_triggered),
        "infinite_move": result.infinite_move,
        "terminal_winner": player_name(result.terminal_winner),
        "termination": None if result.termination is None else result.termination.value,
        "board_snapshot": list(result.board_snapshot),
        "result_to_move": None if result.state is None else player_name(result.state.to_move),
        "result_state_key_hex": None if result.state is None else canonical_state_key_hex(result.state),
    }


def expected_successors_by_line(corpus: Path) -> dict[int, list[dict[str, object]]]:
    results: dict[int, list[dict[str, object]]] = {}
    with corpus.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            state = GameState(tuple(record["state"]), parse_player(record["to_move"]))
            entries = []
            for move in sorted(legal_moves(state), key=encode_move):
                entries.append(result_summary(move, apply_move(state, move)))
            results[line_number] = entries
    return results


def actual_successors_by_line(corpus: Path) -> dict[int, list[dict[str, object]]]:
    cargo = resolve_cargo()
    command = [
        cargo,
        "run",
        "--quiet",
        "-p",
        "bao_solver_core",
        "--bin",
        "successor_corpus",
        "--",
        str(corpus),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        if completed.stdout:
            print(completed.stdout, end="")
        if completed.stderr:
            print(completed.stderr, end="", file=sys.stderr)
        raise RuntimeError(f"native successor check failed with exit code {completed.returncode}")

    results: dict[int, list[dict[str, object]]] = {}
    for line in completed.stdout.splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        results[int(record["line_number"])] = list(record["successors"])
    return results


def main(corpus: Path) -> int:
    expected = expected_successors_by_line(corpus)
    actual = actual_successors_by_line(corpus)

    if expected.keys() != actual.keys():
        extra_native = sorted(actual.keys() - expected.keys())
        missing_native = sorted(expected.keys() - actual.keys())
        raise AssertionError(
            f"Mismatched line coverage. extra_native={extra_native} missing_native={missing_native}"
        )

    for line_number in sorted(expected):
        if expected[line_number] != actual[line_number]:
            raise AssertionError(
                "Line {} successor mismatch.\nexpected={}\nactual={}".format(
                    line_number,
                    json.dumps(expected[line_number], sort_keys=True),
                    json.dumps(actual[line_number], sort_keys=True),
                )
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
