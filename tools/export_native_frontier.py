from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys


RULESPEC_VERSION = "rulespec-v1.0.0-draft"


def resolve_cargo() -> str:
    cargo = shutil.which("cargo")
    if cargo:
        return cargo

    home = Path.home()
    candidates = [
        home / ".cargo" / "bin" / "cargo.exe",
        home / ".cargo" / "bin" / "cargo",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    raise FileNotFoundError("Could not locate cargo on PATH or under ~/.cargo/bin.")


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(depth: int, output: Path, manifest: Path, release: bool) -> int:
    cargo = resolve_cargo()
    command = [cargo, "run", "--quiet"]
    if release:
        command.append("--release")
    command.extend(
        [
            "-p",
            "bao_solver_core",
            "--bin",
            "export_frontier",
            "--",
            "--depth",
            str(depth),
        ]
    )
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        if completed.stdout:
            print(completed.stdout, end="")
        if completed.stderr:
            print(completed.stderr, end="", file=sys.stderr)
        return completed.returncode

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(completed.stdout, encoding="ascii")
    item_count = sum(1 for line in completed.stdout.splitlines() if line.strip())
    payload_bytes = output.stat().st_size
    sha256 = sha256_path(output)

    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest_payload = {
        "artifact_type": "canonical_state_shard_jsonl",
        "rulespec_version": RULESPEC_VERSION,
        "code_revision": "workspace-unversioned",
        "item_count": item_count,
        "payload_bytes": payload_bytes,
        "sha256": sha256,
        "notes": [
            f"depth={depth}",
            "source=initial_position",
            "representation=canonical_state_jsonl",
            f"profile={'release' if release else 'debug'}",
        ],
    }
    manifest.write_text(json.dumps(manifest_payload, indent=2, sort_keys=True) + "\n", encoding="ascii")
    print(f"payload={output}")
    print(f"manifest={manifest}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--depth", type=int, default=6, help="Number of ply layers to export from the initial state.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/shards/frontier_depth6.jsonl"),
        help="Output JSONL path.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("artifacts/shards/frontier_depth6.manifest.json"),
        help="Manifest JSON path.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Run without --release.",
    )
    args = parser.parse_args()
    sys.exit(main(args.depth, args.output, args.manifest, release=not args.debug))
