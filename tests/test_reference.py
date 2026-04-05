import unittest

from bao.reference import (
    Direction,
    Move,
    MoveKind,
    Player,
    apply_move,
    canonical_key,
    initial_state,
    legal_moves,
    pit_index,
    pit_sequence,
    preview_first_sowing,
    reflect_columns,
    rotate_180_and_swap_players,
    state_from_rows,
    winner,
)


class ReferenceEngineTests(unittest.TestCase):
    def test_initial_state_has_expected_shape(self) -> None:
        state = initial_state()
        self.assertEqual(len(state.pits), 32)
        self.assertEqual(sum(state.pits), 64)
        self.assertEqual(state.to_move, Player.SOUTH)
        self.assertTrue(all(value == 2 for value in state.pits))

    def test_regular_sowing_starts_at_next_pit(self) -> None:
        sequence = pit_sequence(
            Player.SOUTH,
            pit_index(Player.SOUTH, "inner", 1),
            Direction.CLOCKWISE,
            2,
            include_start=False,
        )
        expected = (
            pit_index(Player.SOUTH, "inner", 2),
            pit_index(Player.SOUTH, "inner", 3),
        )
        self.assertEqual(sequence, expected)

    def test_capture_resowing_includes_the_kichwa(self) -> None:
        sequence = pit_sequence(
            Player.SOUTH,
            pit_index(Player.SOUTH, "inner", 1),
            Direction.CLOCKWISE,
            2,
            include_start=True,
        )
        expected = (
            pit_index(Player.SOUTH, "inner", 1),
            pit_index(Player.SOUTH, "inner", 2),
        )
        self.assertEqual(sequence, expected)

    def test_preview_of_initial_capture_uses_next_pit_semantics(self) -> None:
        state = initial_state()
        preview = preview_first_sowing(
            state,
            Move(pit_index(Player.SOUTH, "inner", 1), Direction.CLOCKWISE),
        )
        self.assertEqual(preview.landing_pit, pit_index(Player.SOUTH, "inner", 3))
        self.assertTrue(preview.capture_possible)

    def test_mandatory_capture_blocks_non_capturing_opening(self) -> None:
        state = initial_state()
        capture_move = Move(pit_index(Player.SOUTH, "inner", 1), Direction.CLOCKWISE)
        takasa_move = Move(pit_index(Player.SOUTH, "inner", 1), Direction.ANTICLOCKWISE)
        moves = legal_moves(state)
        self.assertIn(capture_move, moves)
        self.assertNotIn(takasa_move, moves)

    def test_initial_clockwise_move_has_multi_capture_trace(self) -> None:
        state = initial_state()
        move = Move(pit_index(Player.SOUTH, "inner", 1), Direction.CLOCKWISE)
        result = apply_move(state, move)

        self.assertEqual(result.move_kind, MoveKind.MTAJI)
        self.assertEqual(result.sowings, 10)
        self.assertEqual(sum(1 for event in result.trace if event.capture_triggered), 4)
        self.assertEqual(result.trace[0].path, (1, 2))
        self.assertEqual(result.trace[1].path, (0, 1))
        self.assertEqual(
            result.board_snapshot,
            (3, 1, 0, 4, 4, 4, 1, 5, 3, 3, 0, 3, 3, 0, 3, 3, 2, 0, 0, 2, 2, 2, 0, 0, 2, 2, 2, 2, 2, 2, 2, 2),
        )

    def test_greater_than_fifteen_rule_disables_mtaji_start(self) -> None:
        state = state_from_rows(
            [17, 1, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 1, 0, 0, 0, 0, 0, 0],
            [45, 0, 0, 0, 0, 0, 0, 0],
            to_move=Player.SOUTH,
        )
        preview = preview_first_sowing(
            state,
            Move(pit_index(Player.SOUTH, "inner", 1), Direction.CLOCKWISE),
        )
        self.assertFalse(preview.capture_possible)

    def test_takasa_uses_front_row_when_possible(self) -> None:
        state = state_from_rows(
            [0, 0, 2, 0, 0, 0, 0, 0],
            [2, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 1],
            [59, 0, 0, 0, 0, 0, 0, 0],
            to_move=Player.SOUTH,
        )
        moves = legal_moves(state)
        self.assertTrue(moves)
        self.assertTrue(all(move.start == pit_index(Player.SOUTH, "inner", 3) for move in moves))

    def test_lone_kichwa_cannot_takasa_toward_the_back_row(self) -> None:
        state = state_from_rows(
            [2, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 1],
            [61, 0, 0, 0, 0, 0, 0, 0],
            to_move=Player.SOUTH,
        )
        moves = legal_moves(state)
        self.assertEqual(moves, [Move(pit_index(Player.SOUTH, "inner", 1), Direction.CLOCKWISE)])

    def test_lone_kichwa_front_row_direction_remains_playable(self) -> None:
        state = state_from_rows(
            [2, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 1],
            [61, 0, 0, 0, 0, 0, 0, 0],
            to_move=Player.SOUTH,
        )
        move = Move(pit_index(Player.SOUTH, "inner", 1), Direction.CLOCKWISE)
        result = apply_move(state, move)
        self.assertEqual(result.move_kind, MoveKind.TAKASA)
        self.assertIsNone(result.terminal_winner)
        self.assertIsNotNone(result.state)

    def test_canonical_key_is_stable_under_reflection_and_player_swap(self) -> None:
        state = state_from_rows(
            [3, 0, 0, 4, 0, 0, 1, 0],
            [2, 0, 0, 0, 0, 0, 0, 0],
            [0, 1, 0, 0, 5, 0, 0, 0],
            [48, 0, 0, 0, 0, 0, 0, 0],
            to_move=Player.SOUTH,
        )
        reflected = reflect_columns(state)
        swapped = rotate_180_and_swap_players(state)
        self.assertEqual(canonical_key(state), canonical_key(reflected))
        self.assertEqual(canonical_key(state), canonical_key(swapped))

    def test_winner_reports_no_move_loss(self) -> None:
        state = state_from_rows(
            [1, 1, 1, 1, 1, 1, 1, 1],
            [1, 1, 1, 1, 1, 1, 1, 1],
            [2, 0, 0, 0, 0, 0, 0, 0],
            [46, 0, 0, 0, 0, 0, 0, 0],
            to_move=Player.SOUTH,
        )
        self.assertEqual(winner(state), Player.NORTH)


if __name__ == "__main__":
    unittest.main()
