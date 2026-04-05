import unittest

from bao import SolverMove, compute_sccs, solve_via_scc


class SccSolverTests(unittest.TestCase):
    def test_compute_sccs_groups_cycles(self) -> None:
        edges = [
            [1],
            [0, 2],
            [3],
            [2],
        ]
        component_ids, components = compute_sccs(4, edges)
        self.assertEqual(len(components), 2)
        self.assertEqual(component_ids[0], component_ids[1])
        self.assertEqual(component_ids[2], component_ids[3])
        self.assertNotEqual(component_ids[0], component_ids[2])

    def test_solve_via_scc_solves_acyclic_win_loss_distances(self) -> None:
        moves = [
            [SolverMove(move_code=10, kind="node", target=1), SolverMove(move_code=11, kind="loss")],
            [SolverMove(move_code=20, kind="node", target=2)],
            [SolverMove(move_code=30, kind="loss")],
        ]
        result = solve_via_scc(moves)
        self.assertEqual(result.node_results[2].to_dict(), {"outcome": "loss", "distance": 1, "best_move_code": 30})
        self.assertEqual(result.node_results[1].to_dict(), {"outcome": "win", "distance": 2, "best_move_code": 20})
        self.assertEqual(result.node_results[0].to_dict(), {"outcome": "loss", "distance": 3, "best_move_code": 10})

    def test_solve_via_scc_keeps_pure_cycle_unknown(self) -> None:
        moves = [
            [SolverMove(move_code=10, kind="node", target=1)],
            [SolverMove(move_code=11, kind="node", target=0)],
        ]
        result = solve_via_scc(moves)
        self.assertEqual(result.node_results[0].to_dict(), {"outcome": None, "distance": None, "best_move_code": None})
        self.assertEqual(result.node_results[1].to_dict(), {"outcome": None, "distance": None, "best_move_code": None})

    def test_solve_via_scc_respects_unknown_frontier_edges(self) -> None:
        moves = [
            [SolverMove(move_code=10, kind="unknown"), SolverMove(move_code=11, kind="node", target=1)],
            [SolverMove(move_code=20, kind="loss")],
        ]
        result = solve_via_scc(moves)
        self.assertEqual(result.node_results[1].to_dict(), {"outcome": "loss", "distance": 1, "best_move_code": 20})
        self.assertEqual(result.node_results[0].to_dict(), {"outcome": "win", "distance": 2, "best_move_code": 11})


if __name__ == "__main__":
    unittest.main()
