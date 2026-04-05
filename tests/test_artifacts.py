import json
import tempfile
import unittest
from pathlib import Path

from bao import (
    Direction,
    Move,
    PackedStateKey,
    apply_move,
    canonical_key,
    canonical_state_key_hex,
    initial_state,
    pack_canonical_state,
    pit_index,
    reflect_columns,
    rotate_180_and_swap_players,
    state_from_rows,
    trace_artifact_from_result,
    trace_artifact_to_json,
    unpack_canonical_pits,
    unpack_canonical_state,
    write_trace_artifact,
)
from bao.reference import Player


class ArtifactAndPackingTests(unittest.TestCase):
    def test_pack_roundtrip_for_initial_state(self) -> None:
        state = initial_state()
        packed = pack_canonical_state(state)
        self.assertEqual(unpack_canonical_state(packed).pits, canonical_key(state))

    def test_pack_roundtrip_for_nontrivial_state(self) -> None:
        state = state_from_rows(
            [3, 0, 0, 4, 0, 0, 1, 0],
            [2, 0, 0, 0, 0, 0, 0, 0],
            [0, 1, 0, 0, 5, 0, 0, 0],
            [48, 0, 0, 0, 0, 0, 0, 0],
            to_move=Player.SOUTH,
        )
        packed = pack_canonical_state(state)
        self.assertEqual(unpack_canonical_pits(packed), canonical_key(state))

    def test_packed_key_is_stable_under_symmetry(self) -> None:
        state = state_from_rows(
            [3, 0, 0, 4, 0, 0, 1, 0],
            [2, 0, 0, 0, 0, 0, 0, 0],
            [0, 1, 0, 0, 5, 0, 0, 0],
            [48, 0, 0, 0, 0, 0, 0, 0],
            to_move=Player.SOUTH,
        )
        reflected = reflect_columns(state)
        swapped = rotate_180_and_swap_players(state)
        self.assertEqual(pack_canonical_state(state), pack_canonical_state(reflected))
        self.assertEqual(pack_canonical_state(state), pack_canonical_state(swapped))

    def test_packed_key_fits_sixteen_bytes(self) -> None:
        state = initial_state()
        packed = pack_canonical_state(state)
        self.assertEqual(len(packed.bytes_be), 16)
        self.assertEqual(len(packed.hex), 32)
        self.assertEqual(PackedStateKey.from_bytes(packed.bytes_be), packed)

    def test_trace_artifact_json_is_deterministic(self) -> None:
        state = initial_state()
        move = Move(pit_index(Player.SOUTH, "inner", 1), Direction.CLOCKWISE)
        result = apply_move(state, move)
        artifact = trace_artifact_from_result(state, move, result)
        first = trace_artifact_to_json(artifact)
        second = trace_artifact_to_json(artifact)
        self.assertEqual(first, second)
        payload = json.loads(first)
        self.assertEqual(payload["rulespec_version"], "rulespec-v1.0.0-draft")
        self.assertEqual(payload["source_state_key_hex"], canonical_state_key_hex(state))

    def test_trace_artifact_writer_emits_ascii_jsonl(self) -> None:
        state = initial_state()
        move = Move(pit_index(Player.SOUTH, "inner", 1), Direction.CLOCKWISE)
        result = apply_move(state, move)
        artifact = trace_artifact_from_result(state, move, result)

        with tempfile.TemporaryDirectory() as tmpdir:
            destination = write_trace_artifact(Path(tmpdir) / "trace.json", artifact)
            payload = destination.read_text(encoding="ascii")
            self.assertTrue(payload.endswith("\n"))
            self.assertEqual(json.loads(payload), json.loads(trace_artifact_to_json(artifact)))


if __name__ == "__main__":
    unittest.main()

