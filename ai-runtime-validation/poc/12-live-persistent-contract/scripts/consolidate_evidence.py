#!/usr/bin/env python3
"""Consolidate the probe iterations into one verifiable evidence package.

Claims in `reports/phase-4/live-persistent-adapter-contract.md` span several
bounded iterations, and `validation_provenance_sha256` must cover all of them.
This assembles every iteration report into a single package whose
`manifest.sha256` digest is that provenance value, and records which iteration is
authoritative for each gate so a reader can trace any claim to a file.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

POC_ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = POC_ROOT / "artifacts"

# Each gate's authoritative iteration.  Where a later iteration corrected a probe
# defect, the later run is authoritative and the earlier one is retained as
# negative evidence rather than deleted.
AUTHORITATIVE: dict[str, str] = {
    "G1": "20260805T160420Z-3af6a8",
    "G2": "20260805T162330Z-c84384",
    "G3": "20260805T160420Z-3af6a8",
    "G4": "20260805T160420Z-3af6a8",
    "G5": "20260805T162830Z-b2ca48",
    "G6": "20260805T160420Z-3af6a8",
    "Q1": "20260805T163624Z-d5cd00",
    "G3_codex": "20260805T163624Z-d5cd00",
    "G4_codex": "20260805T163624Z-d5cd00",
}

# The Claude detector rebind is packaged separately rather than folded into the
# package above.  That package's digest is pinned in `adapters/cli.py` as Codex's
# validation provenance, and regenerating it would invalidate the pin, so a new
# promotion gets a new package that names the earlier one as a dependency.
REBIND_AUTHORITATIVE: dict[str, str] = {
    "G2_claude": "20260805T172349Z-34303d",
    "G2_codex": "20260805T172349Z-34303d",
}

REBIND_ITERATIONS: list[dict[str, str]] = [
    {
        "run_id": "20260805T171837Z-bc92cc",
        "role": (
            "G2 re-run adding live candidate-pattern trials; the declared Claude "
            "detectors still failed, no model call"
        ),
        "gates": "G2",
    },
    {
        "run_id": "20260805T172349Z-34303d",
        "role": (
            "G2 authoritative run after rebinding the Claude detectors to 2.1.222; "
            "both adapters reached READY on the declared production path, no model call"
        ),
        "gates": "G2",
    },
]

ITERATIONS: list[dict[str, str]] = [
    {
        "run_id": "20260805T155910Z-52067a",
        "role": "harness validation, no model call",
        "gates": "harness",
    },
    {
        "run_id": "20260805T160410Z-1b2f3f",
        "role": "harness validation after gate isolation, no model call",
        "gates": "harness",
    },
    {
        "run_id": "20260805T160420Z-3af6a8",
        "role": "first full live run",
        "gates": "G1 G2 G3 G4 G5 G6 Q1",
    },
    {
        "run_id": "20260805T161436Z-8db913",
        "role": "G2 re-run adding bounded diagnostic marker capture, no model call",
        "gates": "G2",
    },
    {
        "run_id": "20260805T161822Z-7ee83d",
        "role": "G2 re-run adding disposable interactive-gate clearing, no model call",
        "gates": "G2",
    },
    {
        "run_id": "20260805T162330Z-c84384",
        "role": "G2 authoritative run: declared production path plus disposable path",
        "gates": "G2",
    },
    {
        "run_id": "20260805T162830Z-b2ca48",
        "role": "G5 authoritative run; Q1 blocked by a probe rollout-snapshot defect",
        "gates": "G5 Q1",
    },
    {
        "run_id": "20260805T163202Z-03f6c1",
        "role": "Q1 re-run; codex exec blocked on inherited stdin and timed out",
        "gates": "Q1",
    },
    {
        "run_id": "20260805T163624Z-d5cd00",
        "role": "Q1 authoritative run after stdin=DEVNULL correction",
        "gates": "Q1 G3_codex G4_codex",
    },
]


def digest(value: bytes | str) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


PACKAGES: dict[str, dict[str, Any]] = {
    "consolidated-live-persistent-contract": {
        "subject": "live-persistent-adapter-contract",
        "authoritative": AUTHORITATIVE,
        "iterations": ITERATIONS,
        "depends_on": None,
    },
    "consolidated-claude-detector-rebind": {
        "subject": "claude-detector-rebind",
        "authoritative": REBIND_AUTHORITATIVE,
        "iterations": REBIND_ITERATIONS,
        "depends_on": {
            "package": "consolidated-live-persistent-contract",
            "validation_provenance_sha256": (
                "db6a6b4febf6b671e9773125f1c2dba50c162ed1c3c0a41b42b592fcff585dd5"
            ),
            "why": (
                "Holds the G2 lineage this rebind corrects: the first failure, the "
                "bounded diagnostic capture, the disposable gate clearing, and the "
                "declared-versus-disposable split. Those iterations are referenced "
                "rather than copied so their live-call totals are not counted twice."
            ),
        },
    },
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default="consolidated-live-persistent-contract")
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite an existing package; refused by default because a package "
        "digest may already be pinned as validation provenance",
    )
    args = parser.parse_args()
    if args.name not in PACKAGES:
        raise SystemExit(f"unknown package: {args.name}; known: {sorted(PACKAGES)}")
    package = PACKAGES[args.name]
    target = ARTIFACTS / args.name
    if target.exists():
        if not args.force:
            raise SystemExit(
                f"{target} already exists and its digest may be pinned as validation "
                "provenance; regenerating would invalidate the pin (pass --force to override)"
            )
        shutil.rmtree(target)
    target.mkdir(parents=True)

    calls = 0
    records: list[dict[str, Any]] = []
    for iteration in package["iterations"]:
        source = ARTIFACTS / iteration["run_id"] / "live-contract-evidence.json"
        if not source.is_file():
            raise SystemExit(f"missing iteration evidence: {source}")
        payload = json.loads(source.read_text(encoding="utf-8"))
        copied = target / f"iteration-{iteration['run_id']}-evidence.json"
        write_json(copied, payload)
        calls += int(payload.get("live_calls", {}).get("total", 0))
        records.append(
            {
                **iteration,
                "decision": payload.get("decision"),
                "live_calls": payload.get("live_calls"),
                "gate_summary": payload.get("gate_summary"),
                "iterations_recorded": len(payload.get("iterations", [])),
                "evidence_file": copied.name,
                "evidence_sha256": digest(copied.read_bytes()),
            }
        )

    index = {
        "format": "ai-runtime-evidence/v2",
        "format_version": 2,
        "subject": package["subject"],
        "consolidated_at": dt.datetime.now(dt.timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        "authoritative_iteration_per_gate": package["authoritative"],
        "iterations": records,
        "depends_on": package["depends_on"],
        "cumulative_live_calls": calls,
        "live_call_budget": 30,
        "budget_respected": calls <= 30,
        "provenance_definition": (
            "validation_provenance_sha256 is the SHA-256 of this package's "
            "manifest.sha256, reproducible with `sha256sum manifest.sha256`."
        ),
    }
    write_json(target / "index.json", index)
    write_json(target / "portable-git-evidence.json", [])

    manifest_lines = [
        f"{digest(path.read_bytes())}  {path.relative_to(target)}"
        for path in sorted(
            item for item in target.rglob("*") if item.is_file() and item.name != "manifest.sha256"
        )
    ]
    manifest = target / "manifest.sha256"
    manifest.write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
    provenance = digest(manifest.read_bytes())
    print(f"cumulative_live_calls: {calls}/30")
    print(f"package: {target}")
    print(f"validation_provenance_sha256: {provenance}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
