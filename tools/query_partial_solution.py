from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bao import (
    decode_native_state_record,
    decode_solution_record,
    find_local_id_by_state_key,
    load_shard_bytes,
    parse_native_header,
    parse_solution_header,
)


def main(
    state_binary: Path,
    solution_binary: Path,
    local_id: int | None,
    state_key_hex: str | None,
) -> int:
    state_raw = load_shard_bytes(state_binary)
    solution_raw = load_shard_bytes(solution_binary)

    if (local_id is None) == (state_key_hex is None):
        raise ValueError("exactly one of --local-id or --state-key-hex must be provided")

    resolved_local_id = local_id
    if resolved_local_id is None:
        resolved_local_id = find_local_id_by_state_key(state_raw, state_key_hex)
        if resolved_local_id is None:
            raise ValueError("state key was not found in the state shard")

    result = {
        "state_header": parse_native_header(state_raw, b"BAOSTATE").to_dict(),
        "solution_header": parse_solution_header(solution_raw).to_dict(),
        "state": decode_native_state_record(state_raw, resolved_local_id).to_dict(),
        "solution": decode_solution_record(solution_raw, resolved_local_id).to_dict(),
    }
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
        "--solution-binary",
        type=Path,
        default=Path("artifacts/solve/slice_partial_depth6.bin"),
        help="Partial solution shard path.",
    )
    lookup = parser.add_mutually_exclusive_group(required=True)
    lookup.add_argument("--local-id", type=int, help="Local state ID to inspect.")
    lookup.add_argument(
        "--state-key-hex",
        type=str,
        help="Canonical 16-byte state key in hex for binary-search lookup.",
    )
    args = parser.parse_args()
    raise SystemExit(main(args.state_binary, args.solution_binary, args.local_id, args.state_key_hex))
