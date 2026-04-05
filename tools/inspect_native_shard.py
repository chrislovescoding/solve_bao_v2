from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct
import sys


HEADER = struct.Struct("<8sHHHHQQQ24s")
KNOWN_MAGICS = {
    b"BAOSTATE": "state",
    b"BAOEDGE!": "edge",
    b"BAOADJ!!": "adjacency",
    b"BAOSOLVE": "solution",
}


def inspect(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    if len(raw) < HEADER.size:
        raise ValueError(f"{path} is smaller than the fixed 64-byte shard header")

    magic, format_version, header_bytes, record_bytes, depth, record_count, payload_bytes, aux_count, rulespec = (
        HEADER.unpack_from(raw, 0)
    )
    rulespec_version = rulespec.rstrip(b"\x00").decode("ascii")
    actual_payload_bytes = len(raw) - HEADER.size

    return {
        "path": str(path),
        "kind": KNOWN_MAGICS.get(magic, "unknown"),
        "magic": magic.decode("ascii", errors="replace"),
        "format_version": format_version,
        "header_bytes": header_bytes,
        "record_bytes": record_bytes,
        "depth": depth,
        "record_count": record_count,
        "payload_bytes_header": payload_bytes,
        "payload_bytes_actual": actual_payload_bytes,
        "aux_count": aux_count,
        "rulespec_version": rulespec_version,
        "filesize_bytes": len(raw),
        "payload_bytes_match": payload_bytes == actual_payload_bytes,
    }


def main(paths: list[Path]) -> int:
    reports = [inspect(path) for path in paths]
    print(json.dumps(reports if len(reports) > 1 else reports[0], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path, help="One or more native shard files to inspect.")
    args = parser.parse_args()
    sys.exit(main(args.paths))
