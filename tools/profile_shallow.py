from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bao.reference import MoveKind, apply_move, canonical_key, initial_state, legal_moves


def main(max_depth: int = 4) -> None:
    layers: dict[int, set] = {0: {initial_state()}}
    discovered = {initial_state()}
    discovered_canonical = {canonical_key(initial_state())}
    overall_branching: list[int] = []
    overall_sowings: list[int] = []
    overall_takasa_sowings: list[int] = []
    overall_mtaji_sowings: list[int] = []
    terminal_results = 0

    for depth in range(max_depth):
        current = layers.get(depth, set())
        next_layer = layers.setdefault(depth + 1, set())
        layer_move_kind_counts = defaultdict(int)
        layer_branching: list[int] = []
        layer_sowings: list[int] = []
        layer_terminals = 0
        layer_canonical = {canonical_key(state) for state in current}

        for state in current:
            moves = legal_moves(state)
            layer_branching.append(len(moves))
            overall_branching.append(len(moves))

            for move in moves:
                result = apply_move(state, move)
                layer_sowings.append(result.sowings)
                overall_sowings.append(result.sowings)
                layer_move_kind_counts[result.move_kind.value] += 1

                if result.move_kind is MoveKind.MTAJI:
                    overall_mtaji_sowings.append(result.sowings)
                else:
                    overall_takasa_sowings.append(result.sowings)

                if result.terminal_winner is not None:
                    layer_terminals += 1
                    terminal_results += 1
                    continue

                next_state = result.state
                if (
                    next_state is not None
                    and next_state not in discovered
                ):
                    discovered.add(next_state)
                    discovered_canonical.add(canonical_key(next_state))
                    next_layer.add(next_state)

        avg_branching = sum(layer_branching) / len(layer_branching) if layer_branching else 0.0
        avg_sowings = sum(layer_sowings) / len(layer_sowings) if layer_sowings else 0.0

        print(
            f"depth={depth} states={len(current)} canonical_states={len(layer_canonical)} "
            f"avg_branching={avg_branching:.3f} moves={sum(layer_branching)} "
            f"avg_sowings={avg_sowings:.3f} mtaji={layer_move_kind_counts['mtaji']} "
            f"takasa={layer_move_kind_counts['takasa']} terminals={layer_terminals}"
        )

    print()
    print(f"total_unique_states_up_to_depth_{max_depth}={len(discovered)}")
    print(f"canonical_unique_states_up_to_depth_{max_depth}={len(discovered_canonical)}")
    if discovered:
        print(f"canonical_reduction_factor={len(discovered) / len(discovered_canonical):.3f}")
    print(f"terminal_results_encountered={terminal_results}")
    if overall_branching:
        print(f"overall_avg_branching={sum(overall_branching) / len(overall_branching):.3f}")
    if overall_sowings:
        print(f"overall_avg_sowings={sum(overall_sowings) / len(overall_sowings):.3f}")
        print(f"overall_max_sowings={max(overall_sowings)}")
    if overall_mtaji_sowings:
        print(f"mtaji_avg_sowings={sum(overall_mtaji_sowings) / len(overall_mtaji_sowings):.3f}")
        print(f"mtaji_max_sowings={max(overall_mtaji_sowings)}")
    if overall_takasa_sowings:
        print(f"takasa_avg_sowings={sum(overall_takasa_sowings) / len(overall_takasa_sowings):.3f}")
        print(f"takasa_max_sowings={max(overall_takasa_sowings)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--depth", type=int, default=4, help="Number of ply layers to profile from the initial state.")
    args = parser.parse_args()
    main(max_depth=args.depth)
