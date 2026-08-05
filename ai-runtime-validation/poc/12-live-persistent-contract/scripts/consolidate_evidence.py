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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default="consolidated-live-persistent-contract")
    args = parser.parse_args()
    target = ARTIFACTS / args.name
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)

    calls = 0
    records: list[dict[str, Any]] = []
    for iteration in ITERATIONS:
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
        "subject": "live-persistent-adapter-contract",
        "consolidated_at": dt.datetime.now(dt.timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        "authoritative_iteration_per_gate": AUTHORITATIVE,
        "iterations": records,
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
