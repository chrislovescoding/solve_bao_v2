from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bao.native_shards import load_shard_bytes, query_native_state_successors


def main(
    state_binary: Path,
    adjacency_binary: Path,
    local_id: int | None,
    state_key_hex: str | None,
) -> int:
    result = query_native_state_successors(
        load_shard_bytes(state_binary),
        load_shard_bytes(adjacency_binary),
        local_id=local_id,
        state_key=state_key_hex,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--state-binary",
        type=Path,
        default=Path("artifacts/shards/native_state_slice_depth6.bin"),
        help="Native binary state shard path.",
    )
    parser.add_argument(
        "--adjacency-binary",
        type=Path,
        default=Path("artifacts/shards/native_adjacency_slice_depth6.bin"),
        help="Native binary adjacency shard path.",
    )
    lookup = parser.add_mutually_exclusive_group(required=True)
    lookup.add_argument("--local-id", type=int, help="Local state ID to inspect.")
    lookup.add_argument(
        "--state-key-hex",
        type=str,
        help="Canonical 16-byte state key in hex for binary-search lookup.",
    )
    args = parser.parse_args()
    sys.exit(main(args.state_binary, args.adjacency_binary, args.local_id, args.state_key_hex))
