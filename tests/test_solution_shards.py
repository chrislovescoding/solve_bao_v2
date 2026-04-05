import tempfile
import unittest
from pathlib import Path

from bao import (
    NativeSolutionRecord,
    decode_all_solution_records,
    decode_solution_record,
    parse_solution_header,
    write_solution_shard,
)


class SolutionShardTests(unittest.TestCase):
    def test_solution_shard_roundtrip(self) -> None:
        records = [
            NativeSolutionRecord(
                local_id=0,
                outcome="loss",
                best_move_code=None,
                distance=0,
                partial=False,
                terminal_seed=True,
                frontier_dependent=False,
            ),
            NativeSolutionRecord(
                local_id=1,
                outcome="win",
                best_move_code=18,
                distance=3,
                partial=False,
                terminal_seed=False,
                frontier_dependent=False,
            ),
            NativeSolutionRecord(
                local_id=2,
                outcome=None,
                best_move_code=None,
                distance=None,
                partial=True,
                terminal_seed=False,
                frontier_dependent=True,
            ),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            destination = Path(tmpdir) / "solution.bin"
            write_solution_shard(destination, records, depth=6, resolved_count=2)
            raw = destination.read_bytes()

            header = parse_solution_header(raw)
            self.assertEqual(header.record_count, 3)
            self.assertEqual(header.aux_count, 2)
            self.assertEqual(header.record_bytes, 8)

            decoded = decode_all_solution_records(raw)
            self.assertEqual([record.to_dict() for record in decoded], [record.to_dict() for record in records])
            self.assertEqual(decode_solution_record(raw, 1).to_dict(), records[1].to_dict())


if __name__ == "__main__":
    unittest.main()
