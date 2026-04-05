from __future__ import annotations

import argparse
from collections import deque
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bao.packing import canonical_state_key_hex
from bao.reference import apply_move, initial_state, legal_moves


def main(depth: int, output: Path) -> None:
    queue = deque([(initial_state(), 0)])
    discovered = {canonical_state_key_hex(initial_state())}
    output.parent.mkdir(parents=True, exist_ok=True)

    with output.open("w", encoding="ascii") as handle:
        while queue:
            state, ply = queue.popleft()
            moves = []

            for move in legal_moves(state):
                result = apply_move(state, move)
                moves.append(
                    {
                        "move_start": move.start,
                        "move_direction": move.direction.value,
                        "move_kind": result.move_kind.value,
                        "sowings": result.sowings,
                        "seeds_sown": result.seeds_sown,
                        "infinite_move": result.infinite_move,
                        "terminal_winner": None if result.terminal_winner is None else ("south" if result.terminal_winner.value == 0 else "north"),
                        "termination": None if result.termination is None else result.termination.value,
                        "result_state_key_hex": None if result.state is None else canonical_state_key_hex(result.state),
                    }
                )

                if ply + 1 < depth and result.state is not None and result.terminal_winner is None:
                    key = canonical_state_key_hex(result.state)
                    if key not in discovered:
                        discovered.add(key)
                        queue.append((result.state, ply + 1))

            record = {
                "canonical_state_key_hex": canonical_state_key_hex(state),
                "state": list(state.pits),
                "to_move": "south" if state.to_move.value == 0 else "north",
                "ply": ply,
                "legal_moves": moves,
            }
            handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--depth", type=int, default=3, help="BFS depth for the emitted reference corpus.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/reference_corpus_depth3.jsonl"),
        help="Output JSONL path.",
    )
    args = parser.parse_args()
    main(args.depth, args.output)

