# Bounded Implementer/Reviewer Loop and Packet Cost Control

## Decision

**Implemented and validated deterministically.** One human request is now bound
to a configured number of Claude/Codex rounds, and every packet sent to a model
is assembled from bounded, evidence-free artifacts.

This closes a gap between the specification and the reference implementation.
Chapters 14, 17, and 18 already required a review/fix limit with human
escalation; the coordinator had no counter, and `CHANGES_REQUESTED` fell through
to the terminal branch of `run_until_gate`. A rejected implementation stopped
silently at a phase nothing could advance.

## What changed

### Bounded loop

- `RuntimeConfig.max_fix_cycles` (default `5`, validated `1..20`). A fix cycle is
  one accepted `changes.requested`; because the nth such event is what would
  dispatch round n+1, a limit of N permits at most N implementer/reviewer rounds.
- `FeatureState` projects `dispatch_rounds`, `fix_cycles`, `cycle_allowance`, and
  a `blocked` overlay. All four are derived by replay, so a restart recovers the
  cycle count without trusting a live process.
- `run_until_gate` now traverses `CHANGES_REQUESTED` by re-granting the writer
  lease on the same worktree and re-dispatching the implementer. It returns
  immediately when the feature is blocked.
- At the limit the Runtime appends `feature.blocked` with reason
  `review_fix_cycle_limit`, carrying cycle and round counts, the effective limit,
  base/reviewed heads, branch, the last review summary and findings, and the
  permitted maintainer actions.
- `override_fix_cycle_limit` appends `feature.unblocked` with operator identity,
  justification, and a new bounded allowance. It rejects an empty justification,
  rejects an allowance above the configured maximum, and rejects a block it does
  not apply to. It never approves a change and never clears findings.
- `approve_merge` and `merge` refuse to act on a blocked feature.

### Packet cost control

Every model turn under the supervised non-interactive transport is a fresh
process that pays for its packet again, so worst-case cost for one request is
`plan packet + max_fix_cycles x (implementation packet + review packet)`.

- The plan now travels as a digest-labelled artifact view restricted to
  `summary`, `steps`, `acceptance_criteria`, and `risks`. Previously the
  implementation and review prompts serialized `state.plan` whole, which carried
  `adapter_evidence` — turn IDs, output digests, byte counts, timings — into
  every turn. That data is durable Event Store evidence and has no effect on the
  model's task.
- Prior findings, changed-path lists, and reported tests are individually capped.
  Truncation is stated inside the packet rather than hidden.
- The assembled packet is rejected above `RuntimeConfig.feature_packet_bytes`
  (default 128 KiB), matching the Chapter 09 budget table.
- A rework packet carries the findings and the exact head they were written
  against. Findings whose reviewed head no longer matches the worktree are
  omitted, because they describe code that no longer exists.

### Correctness defects found while implementing the loop

Two defects were latent only because the loop had never executed twice.

- **Fencing tokens reset.** `LeaseManager.acquire` derived the next token from
  the live lease file, and `revoke` unlinks it. A second grant for the same
  feature therefore issued token 1 again, so a paused writer from an earlier
  cycle would have presented a token the gateway still accepted. Tokens now come
  from a per-feature high-water file that outlives the lease, and the
  re-dispatch test asserts the observed sequence `[1, 2]`.
- **A fix cycle could record no work.** `inspect_implementation` only rejects a
  head equal to the *base*, so on a fix cycle an implementer that committed
  nothing would re-emit the previous head as a new `implementation.ready` and
  consume a round with no change. The coordinator now rejects an unchanged head
  before appending the event.

The `_implement` and `_grant_lease` head checks were widened from "head equals
base" to "head equals the last reviewed head, or base when there is none". The
invariant still detects an unrecorded commit; it no longer misreads a legitimate
prior round as one.

## Non-changes

Merge authority, approval binding, exact-head human override, worktree
isolation, Git-first truth, protected-ref snapshots, replay purity, and the fork
abstraction are unchanged. A block prevents side effects; it grants and withdraws
no authority. No adapter capability was promoted: Claude, Codex, and Antigravity
declarations remain fail-closed for persistent root, native fork, resume, and
structured terminal events.

## Fork economics recorded, not claimed

Chapter 09 now records why the round limit is a cost control and what fork mode
actually buys. The distinction matters and was not previously written down:

- a **synthetic** fork is a fresh session plus a bounded packet. It is cheaper
  than making the child re-derive orientation, but it shares no prefix with the
  root, so nothing is read from a prompt cache;
- a **native** fork branches the root's conversation prefix, and only that mode
  turns the shared prefix into a cache read.

Cache pricing, prefix-match invalidation, TTL expiry, and model-scoping are
recorded as constraints on the design. The chapter also states why fork context
is never merged back into the root: merging it would grow the shared prefix after
every feature, so each later fork would read a larger prefix and every TTL expiry
would rewrite a larger one. The root re-derives a bounded snapshot from the
merged Git range instead, keeping per-feature cost flat over project age.

`native fork` remains unavailable in practice. The installed CLIs expose the
primitives — `claude --fork-session` on 2.1.222, `codex fork` on 0.146.0 — but
help output is not Capability Registry evidence, and the runtime must not claim
the native-fork economics while its declaration is fail-closed. Two open
questions must be answered by a live disposable-repository probe before that
changes:

1. `codex fork` is documented for *interactive* sessions while the runtime drives
   `codex exec`. Whether `codex exec resume <forked_session_id>` drives a session
   created by `codex fork` is unverified.
2. A fork must name its parent by the CLI's own session identifier. The feature
   session factory renders `{parent_session_id}` as the runtime registry ID, not
   a vendor session UUID, so a root would first have to launch with a
   runtime-assigned session ID for the mapping to render correctly.

## Verification

- runtime tests: **52/52 passed** (six new: re-dispatch and merge after a fix,
  limit reached and escalated, configurable limit, bounded maintainer override,
  no-op fix cycle fenced, packets free of transport evidence and within budget);
- contract validation `ci.sh 01 02 03 04 05 06 07 08 10`: **73/73 assertions**;
- `ruff check`, `ruff format --check`, and `mypy` clean across `src`, `tests`,
  and `benchmarks`;
- no live model calls; no adapter capability promoted; no frozen validation
  laboratory file modified.
