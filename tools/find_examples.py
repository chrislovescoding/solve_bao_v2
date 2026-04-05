from __future__ import annotations

from collections import deque
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bao.reference import GameState, MoveKind, apply_move, initial_state, legal_moves, pit_label


def main(max_depth: int = 5) -> None:
    queue = deque([(initial_state(), [], 0)])
    seen: set[GameState] = set()
    first_multi_capture = None
    longest_takasa = None

    while queue:
        state, history, depth = queue.popleft()
        if state in seen:
            continue
        seen.add(state)

        moves = legal_moves(state)
        for move in moves:
            result = apply_move(state, move)
            capture_count = sum(1 for event in result.trace if event.capture_triggered)

            if capture_count >= 2 and first_multi_capture is None:
                first_multi_capture = (history, move, result)

            if result.move_kind is MoveKind.TAKASA:
                if longest_takasa is None or result.sowings > longest_takasa[2].sowings:
                    longest_takasa = (history, move, result)

            if depth + 1 < max_depth and result.state is not None and result.terminal_winner is None:
                queue.append((result.state, history + [move], depth + 1))

        if first_multi_capture is not None and longest_takasa is not None:
            break

    print(f"searched_states={len(seen)}")
    print()
    print("first_multi_capture")
    if first_multi_capture is None:
        print("not found")
    else:
        history, move, result = first_multi_capture
        print(
            f"history_len={len(history)} move={pit_label(move.start)} "
            f"{move.direction.value} sowings={result.sowings}"
        )
        for index, event in enumerate(result.trace, start=1):
            print(
                f"  sowing={index} start={pit_label(event.start)} seeds={event.seeds} "
                f"landing={pit_label(event.landing_pit)} capture={event.capture_triggered} "
                f"captured_count={event.captured_count}"
            )
        print(f"board={result.board_snapshot}")

    print()
    print("longest_takasa")
    if longest_takasa is None:
        print("not found")
    else:
        history, move, result = longest_takasa
        print(
            f"history_len={len(history)} move={pit_label(move.start)} "
            f"{move.direction.value} sowings={result.sowings} seeds_sown={result.seeds_sown}"
        )
        print(f"board={result.board_snapshot}")


if __name__ == "__main__":
    main()
