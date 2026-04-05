import unittest
from pathlib import Path

from bao import (
    decode_all_native_adjacency_records,
    decode_all_native_state_records,
    decode_native_state_record,
    find_local_id_by_state_key,
    load_shard_bytes,
    parse_native_header,
    query_native_state_successors,
)


ROOT = Path(__file__).resolve().parents[1]
STATE_SHARD = ROOT / "artifacts" / "shards" / "native_state_slice_depth6.bin"
ADJACENCY_SHARD = ROOT / "artifacts" / "shards" / "native_adjacency_slice_depth6.bin"


class NativeShardQueryTests(unittest.TestCase):
    def setUp(self) -> None:
        if not STATE_SHARD.exists() or not ADJACENCY_SHARD.exists():
            self.skipTest("native shard artifacts are not present")
        self.state_raw = load_shard_bytes(STATE_SHARD)
        self.adjacency_raw = load_shard_bytes(ADJACENCY_SHARD)

    def test_find_local_id_by_state_key_roundtrips_known_records(self) -> None:
        header = parse_native_header(self.state_raw, b"BAOSTATE")
        sample_ids = [0, 1, 24, header.record_count - 1]
        for local_id in sample_ids:
            record = decode_native_state_record(self.state_raw, local_id)
            self.assertEqual(
                find_local_id_by_state_key(self.state_raw, record.canonical_state_key_hex),
                local_id,
            )

    def test_query_by_state_key_matches_query_by_local_id(self) -> None:
        by_id = query_native_state_successors(self.state_raw, self.adjacency_raw, local_id=24)
        by_key = query_native_state_successors(
            self.state_raw,
            self.adjacency_raw,
            state_key=by_id["state"]["canonical_state_key_hex"],
        )
        self.assertEqual(by_key["state"], by_id["state"])
        self.assertEqual(by_key["successor_count"], by_id["successor_count"])
        self.assertEqual(by_key["successors"], by_id["successors"])

    def test_bulk_decoders_match_single_record_queries(self) -> None:
        states = decode_all_native_state_records(self.state_raw)
        successors = decode_all_native_adjacency_records(
            self.state_raw,
            self.adjacency_raw,
            state_records=states,
        )
        self.assertEqual(len(states), parse_native_header(self.state_raw, b"BAOSTATE").record_count)
        self.assertEqual(states[24].to_dict(), decode_native_state_record(self.state_raw, 24).to_dict())
        self.assertEqual(
            [record.to_dict() for record in successors[24]],
            query_native_state_successors(self.state_raw, self.adjacency_raw, local_id=24)["successors"],
        )


if __name__ == "__main__":
    unittest.main()
