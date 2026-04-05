from __future__ import annotations

import argparse
from collections import deque
from dataclasses import dataclass
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bao.reference import Move, MoveKind, MoveResult, apply_move, canonical_key, initial_state, legal_moves, pit_label


@dataclass(frozen=True)
class Example:
    history: tuple[Move, ...]
    move: Move
    result: MoveResult


def format_move(move: Move) -> str:
    return f"{pit_label(move.start)} {move.direction.value}"


def format_history(history: tuple[Move, ...], move: Move) -> str:
    sequence = [format_move(item) for item in history] + [format_move(move)]
    return " -> ".join(sequence)


def capture_count(result: MoveResult) -> int:
    return sum(1 for event in result.trace if event.capture_triggered)


def better(candidate: Example, incumbent: Example | None, *, metric: str) -> bool:
    if incumbent is None:
        return True

    candidate_value = getattr(candidate.result, metric)
    incumbent_value = getattr(incumbent.result, metric)
    if candidate_value != incumbent_value:
        return candidate_value > incumbent_value

    if capture_count(candidate.result) != capture_count(incumbent.result):
        return capture_count(candidate.result) > capture_count(incumbent.result)

    return format_history(candidate.history, candidate.move) < format_history(incumbent.history, incumbent.move)


def print_example(label: str, example: Example | None) -> None:
    print(label)
    if example is None:
        print("not found")
        print()
        return

    print(f"line={format_history(example.history, example.move)}")
    print(
        f"move_kind={example.result.move_kind.value} sowings={example.result.sowings} "
        f"seeds_sown={example.result.seeds_sown} captures={capture_count(example.result)}"
    )
    print(f"final_board={example.result.board_snapshot}")
    for index, event in enumerate(example.result.trace, start=1):
        print(
            f"  sowing={index} start={pit_label(event.start)} landing={pit_label(event.landing_pit)} "
            f"seeds={event.seeds} capture={event.capture_triggered} captured_count={event.captured_count}"
        )
    print()


def main(max_depth: int = 5) -> None:
    root = initial_state()
    queue = deque([(root, tuple(), 0)])
    discovered = {canonical_key(root)}

    longest_move: Example | None = None
    longest_takasa: Example | None = None
    most_captures: Example | None = None
    explored_states = 0

    while queue:
        state, history, depth = queue.popleft()
        explored_states += 1

        for move in legal_moves(state):
            result = apply_move(state, move)
            example = Example(history=history, move=move, result=result)

            if better(example, longest_move, metric="sowings"):
                longest_move = example

            if result.move_kind is MoveKind.TAKASA and better(example, longest_takasa, metric="sowings"):
                longest_takasa = example

            if most_captures is None or capture_count(result) > capture_count(most_captures.result):
                most_captures = example

            if depth + 1 >= max_depth or result.state is None or result.terminal_winner is not None:
                continue

            key = canonical_key(result.state)
            if key in discovered:
                continue
            discovered.add(key)
            queue.append((result.state, history + (move,), depth + 1))

    print(f"explored_states={explored_states}")
    print(f"canonical_discovered_states={len(discovered)}")
    print()
    print_example("longest_move", longest_move)
    print_example("longest_takasa", longest_takasa)
    print_example("most_captures", most_captures)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--depth", type=int, default=5, help="Number of ply layers to explore from the initial state.")
    args = parser.parse_args()
    main(max_depth=args.depth)
