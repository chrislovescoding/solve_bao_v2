from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bao.native_shards import load_shard_bytes, parse_native_header
from bao.solution_shards import decode_all_solution_records, parse_solution_header


def main(state_binary: Path, solution_binary: Path, summary_json: Path) -> int:
    state_header = parse_native_header(load_shard_bytes(state_binary), b"BAOSTATE")
    solution_raw = load_shard_bytes(solution_binary)
    solution_header = parse_solution_header(solution_raw)
    summary = json.loads(summary_json.read_text(encoding="ascii"))
    records = decode_all_solution_records(solution_raw)

    if solution_header.record_count != state_header.record_count:
        raise AssertionError(
            f"solution/state count mismatch. solution={solution_header.record_count} state={state_header.record_count}"
        )
    if solution_header.record_count != len(records):
        raise AssertionError(
            f"solution header/decoded count mismatch. header={solution_header.record_count} decoded={len(records)}"
        )
    if solution_header.record_count != int(summary["state_count"]):
        raise AssertionError(
            f"solution/summary state count mismatch. solution={solution_header.record_count} summary={summary['state_count']}"
        )

    resolved_count = sum(1 for record in records if record.outcome is not None)
    if resolved_count != solution_header.aux_count:
        raise AssertionError(
            f"solution resolved count mismatch. header={solution_header.aux_count} actual={resolved_count}"
        )
    if resolved_count != int(summary["resolved_state_count"]):
        raise AssertionError(
            f"solution/summary resolved count mismatch. solution={resolved_count} summary={summary['resolved_state_count']}"
        )

    root_local_id = int(summary["root_local_id"])
    root_record = records[root_local_id]
    root_best_move_code = summary.get("root_best_move_code")
    root_distance = summary.get("root_distance")
    if root_record.outcome != (None if summary["root_status"] == "unknown" else summary["root_status"]):
        raise AssertionError(
            f"root outcome mismatch. solution={root_record.outcome} summary={summary['root_status']}"
        )
    if root_record.best_move_code != root_best_move_code:
        raise AssertionError(
            f"root best-move mismatch. solution={root_record.best_move_code} summary={root_best_move_code}"
        )
    if root_record.distance != root_distance:
        raise AssertionError(
            f"root distance mismatch. solution={root_record.distance} summary={root_distance}"
        )

    print(f"validated_solution_records={len(records)}")
    print(f"resolved_solution_records={resolved_count}")
    print(f"root_local_id={root_local_id}")
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
    parser.add_argument(
        "--summary-json",
        type=Path,
        default=Path("artifacts/solve/slice_partial_depth6.json"),
        help="Partial solution summary JSON path.",
    )
    args = parser.parse_args()
    raise SystemExit(main(args.state_binary, args.solution_binary, args.summary_json))
