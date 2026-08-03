# AI Multi-Agent Runtime V2.2 — Architecture Validation Workspace

## Purpose

This workspace provides a structured, repeatable **Proof of Concept (PoC) validation laboratory** for the [AI Multi-Agent Runtime V2.2 Architecture Specification](../docs/README.md). It experimentally proves that every important architectural assumption in V2.2 can work in practice.

> **This is NOT a production implementation.** No runtime, scheduler, event bus, knowledge runtime, session manager, or Git gateway is built here. The workspace validates architectural feasibility through lightweight experiments, scripts, and structured evidence collection.

## Architecture Specification

The frozen V2.2 specification lives under [`../docs/`](../docs/README.md) and is treated as **read-only**. This validation workspace references V2.2 terminology, invariants, and component definitions without modifying them.

## Workspace Structure

```
ai-runtime-validation/
├── README.md                    ← You are here
├── ROADMAP.md                   ← Phased execution plan with dependencies
├── experiment-log.md            ← Append-only engineering journal
├── reports/                     ← Phase report templates
│   ├── phase-01-report.md
│   ├── phase-02-report.md
│   ├── ...
│   └── phase-10-report.md
├── scripts/                     ← Shared helper scripts
│   ├── validate_environment.sh
│   ├── cleanup.sh
│   ├── start_tmux_demo.sh
│   ├── capture_tmux_output.sh
│   ├── run_phase01.sh
│   └── run_phase02.sh
├── fixtures/                    ← Shared test fixtures
│   └── .gitkeep
├── tmp/                         ← Temporary execution artifacts
│   └── .gitkeep
└── poc/                         ← Proof of Concept experiments
    ├── 01-tmux-runtime/         ← tmux as runtime substrate
    ├── 02-event-protocol/       ← JSON event envelope and Event Store
    ├── 03-session-resume/       ← Persistent sessions and recovery
    ├── 04-capability-registry/  ← Adapter capability gating
    ├── 05-knowledge-runtime/    ← Knowledge Snapshots and Evolution
    ├── 06-review-loop/          ← Feature/review lifecycle and approval
    ├── 07-scheduler/            ← Eligibility Scheduler and Dispatcher
    ├── 08-chaos/                ← Fault injection and recovery
    ├── 09-performance/          ← Benchmarks and token budgets
    └── 10-end-to-end/           ← Full integrated workflow validation
```

## Each PoC Contains

| File | Purpose |
| --- | --- |
| `README.md` | Objective, scope, success criteria, architecture assumptions |
| `DESIGN.md` | Experiment design, architecture mapping, runtime topology |
| `RUN.md` | Prerequisites, execution steps, commands, expected output |
| `EXPECTED.md` | Measurable pass/fail criteria |
| `RESULT.md` | Template for recording actual results |
| `ISSUES.md` | Template for discovered issues |
| `scripts/` | PoC-specific automation scripts |
| `fixtures/` | Test data, sample events, configuration |

## How to Use This Workspace

### 1. Read the Architecture Specification

Start with [`../docs/README.md`](../docs/README.md) and the [Architecture Overview](../docs/architecture/01-architecture-overview.md).

### 2. Validate Prerequisites

```bash
./scripts/validate_environment.sh
```

### 3. Execute a PoC

Each PoC can be run independently:

```bash
cd poc/01-tmux-runtime
cat README.md          # Understand the objective
cat RUN.md             # Follow execution steps
./scripts/run_all.sh   # Run the experiment
```

Run the entire suite from this directory with:

```bash
./run-all.sh
```

Run selected PoCs with `./run-selected.sh 01 02`, or use `./ci.sh` as the CI entrypoint. Every run stores an environment record, assertion-level JSON reports, a Markdown summary, a failure report, captured artifacts, and JUnit XML under a unique `artifacts/<run-id>/` directory.

### 4. Compare Results

After execution, compare observed behavior against `EXPECTED.md` and record findings in `RESULT.md`.

### 5. Follow the Roadmap

Execute phases in order defined in [`ROADMAP.md`](ROADMAP.md). Each phase builds on validated assumptions from prior phases.

## Prerequisites

| Requirement | Minimum Version | Purpose |
| --- | --- | --- |
| `bash` | 4.0+ | Script execution |
| `tmux` | 3.0+ | Runtime substrate validation |
| `git` | 2.30+ | Worktree and merge validation |
| `jq` | 1.6+ | JSON event processing |
| `openssl` | 1.1+ | SHA-256 integrity hashing |
| `python3` | 3.8+ | Validation engine and measured test workloads |
| Python `jsonschema` | Draft-07 support | Event envelope contract validation |

## Architectural Invariants Under Validation

| ID | Invariant | Primary PoC |
| --- | --- | --- |
| INV-01 | Git is the durable source of truth | 05, 08, 10 |
| INV-02 | Root sessions never write feature code | 06, 10 |
| INV-03 | A worktree has at most one writer | 06, 08 |
| INV-04 | Only Claude reviewer authority approves merge | 06, 10 |
| INV-05 | Knowledge sync occurs only after integrated Git change | 05, 10 |
| INV-06 | Normal execution does not use resume | 03, 10 |
| INV-07 | Event producers do not block on consumers | 01, 07, 10 |
| INV-08 | Feature sessions are disposable | 01, 06, 10 |
| INV-09 | Every state change has correlation and provenance | 02, 10 |
| INV-10 | Raw prompts are not operational logs by default | 09, 10 |

## Success Criteria

After completion, an engineer unfamiliar with this project should be able to:

1. Read the V2.2 Architecture Specification
2. Execute every PoC independently
3. Compare expected vs. actual behavior
4. Determine whether each architectural assumption has been experimentally validated
5. Know exactly what remains before production implementation

## Related Documents

- [Architecture Specification](../docs/README.md)
- [V2 Architecture Review](../docs/architecture/05-v2-architecture-review.md)
- [ADR-011 — V2 Design Decisions](../docs/architecture/06-v2-design-decisions.md)
- [Testing and Benchmark Strategy](../docs/implementation/04-testing-benchmarks.md)
- [Glossary and Reference](../docs/appendix/03-glossary-reference.md)
