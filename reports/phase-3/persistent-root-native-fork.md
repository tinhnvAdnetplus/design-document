# Persistent Root and Native Feature Fork Transport

## Decision

The runtime now has a persistent-root lifecycle, a capability-bound feature
session factory, and a structured terminal-event channel that is independent
of tmux pane/model transcript parsing. The deterministic runtime contract is
implemented and validated.

The installed Claude and Codex persistent model transports are **not
production-ready**. Their adapter-owned declarations remain fail-closed for
persistent root readiness, native fork/resume, and structured terminal events
because this increment performed discovery only and no disposable live model
contract. The implementation does not infer capability from help text or claim
that a TUI pane is a protocol.

## Implemented surface

`FeatureSessionFactory` provides the requested unified operations:

- `create_from_root`, `native_fork`, and `synthetic_fork`;
- `observe` / `readiness`;
- `deliver_event_reference`, `collect_structured_event`, and
  `accept_structured_event`;
- durable `acknowledge_structured_event`;
- `resume_or_reconstruct`, `terminate`, `replace_root`, and `reconcile`.

The factory records feature ID, role, attempt, parent root, explicit fork mode,
adapter/version, policy and capability revision/digest, Git base, optional
writer worktree, recovery provenance, lifecycle state, and cleanup evidence.
A feature-role attempt has a unique generated identity and can never be reused.

`SessionSupervisor` now distinguishes legacy, root, and feature sessions. A
reattach requires the registry/tmux runtime identity, adapter/version, launch
contract, role, cwd, repository identity digest, policy revision, capability
revision/digest, feature lineage, and worktree binding to agree. tmux pane data
is used only ephemerally for bounded readiness/health observation.

## Root lifecycle

One active root alias per adapter is stored by the runtime. Roots are read-only,
have no feature ID, parent, worktree binding, or writer lease, and remain alive
when feature children terminate. A runtime restart reattaches the same root only
after identity, cwd, repository, policy, capability, and readiness checks.

Normal workflow has no root restart operation. Controlled replacement is:

```text
READY/BUSY -> DRAINING -> TERMINATING -> TERMINATED
                                     -> replacement reconstruction
```

The replacement receives a new runtime session ID and the old record keeps the
`replaced_by` lineage. Existing children are not killed or silently remapped;
reconciliation reports them as children of a terminated parent until their
bounded feature work ends or recovery policy acts.

## Capability-driven fork decision

`PersistentAdapterDeclaration` is owned by the adapter, bound to the exact
observed adapter version through its declaration revision/digest, and registered
fresh in `CapabilityRegistry`. It separately declares:

- persistent root readiness;
- synthetic launch mapping;
- native fork command mapping;
- resume command mapping;
- structured terminal-event compatibility;
- validation provenance;
- roles, write scope, temporary status, and merge-authority eligibility.

Native fork is selectable only when its mapping, structured channel, and
validation provenance are all `validated`. Otherwise the factory selects an
explicitly declared synthetic fork with reconstruction provenance, or raises
`CapabilityUnavailableError`. There is no best-effort native attempt and no
silent fallback.

The deterministic fixture validates both native and synthetic branches. A
successful native command that does not establish the expected runtime identity
and readiness enters `RECOVERY_REQUIRED`.

## Structured terminal-event channel

`StructuredTerminalEventChannel` stores a permission-restricted immutable
inbox packet and intent digest before notification. tmux receives only:

```text
EVENT ref-<generated-safe-id>
```

User text, prompt, diff, schema, path, and secrets are not sent through
`send-keys`. The runtime client resolves the reference under the bound session
inbox and emits an identity/digest-correlated structured event to the runtime
outbox.

The runtime validates that event before Event Store append. It writes a durable
idempotent acknowledgement only after append succeeds, then removes the inbox,
outbox, and delivery notice. If append succeeds and acknowledgement is lost,
Event Store replay supplies the accepted event ID to reconciliation; the stale
result is acknowledged and removed without terminal input or prompt resend.
Replay itself remains a pure projection fold and never calls a model, sends
keys, or mutates Git.

Packets are capped at 128 KiB and structured results at 1 MiB. Invalid or
oversized results are removed after retaining only hash, byte count, timing,
exit status, and a bounded non-content diagnostic. The deterministic channel
does not persist raw pane, stdout, stderr, or model transcripts.

The transitional non-interactive worker was also hardened: new response spool
records contain only a task-shaped structured candidate plus non-content output
metrics. On restart, legacy raw response files are migrated in place to that
shape before recovery proceeds.

## Adapter profiles

| Adapter | Root/fork state in this increment | Authority |
| --- | --- | --- |
| Claude 2.1.197 | root, native fork, resume, and persistent structured channel fail-closed pending disposable live validation; synthetic mapping declared | production planner/reviewer default; default merge authority disabled; only adapter eligible after explicit validation provenance |
| Codex 0.146.0 | root is configured `read-only`; root, native fork, resume, and persistent structured channel fail-closed; synthetic mapping declared | implementer only; no merge authority |
| Antigravity 1.1.10 | temporary, plan sandbox, CLI log disabled, synthetic reconstruction only | advisory only; no merge authority; human exact-head approval remains required |

Codex feature writers are accepted only when cwd equals the runtime-generated
`<worktree_root>/<feature_id>` binding. The integration worktree and arbitrary
directories are rejected. The coordinator's existing lease/fencing, protected
ref/config snapshot, Git-derived head, review gate, and merge checks remain
unchanged. Model-declared commits remain observations only.

Claude merge authority now defaults to disabled. Enabling the only eligible
adapter requires an explicit validation provenance digest; coordinator policy
still rejects every non-Claude or temporary authority claim, and merge approval
continues to bind the exact Git-derived base/head.

## Recovery coverage

Deterministic tests cover:

- restart reattach of a live root and child;
- one root surviving multiple features and child cleanup;
- lost root reconstruction;
- lost resume ID selecting reconstruction;
- failed validated resume followed by explicit synthetic reconstruction;
- dirty Codex worktree preservation with the writer fenced;
- stale tmux identity and adapter/version drift;
- policy/capability drift on restart;
- native command success followed by readiness/identity failure;
- fork completion before a new runtime observes the lifecycle record;
- structured result completion before Event Store acknowledgement;
- Event Store append before result-ack loss without resend;
- idempotent terminate acknowledgement loss;
- controlled root replacement while a child remains alive;
- feature cleanup without root termination;
- invalid output deletion and legacy raw-spool migration;
- Event Store replay with no terminal/model side effects;
- Codex integration-worktree rejection; and
- authority rejection for non-Claude and temporary adapters.

The existing end-to-end suite continues to cover Event Store, Git worktree,
writer lease/fencing, review gate, exact-head human override for Antigravity,
merge, reconciliation, and cleanup. No auto-stage, auto-commit, reset,
dirty-worktree deletion, auto-merge, or replayed side effect was introduced.

## Verification

Validated against implementation commit `12495e3` before the report/evidence
commit:

- runtime tests: **46/46 passed**;
- deterministic root/factory/channel tests: **14/14 passed**;
- contract validation: **82/82 assertions passed**;
- clean-clone runtime tests: **46/46 passed**;
- clean-clone contract validation: **82/82 passed**;
- clean clone began with a clean working tree;
- normative `docs/` diff from `571baf5`: empty;
- discovery-only versions: Claude `2.1.197`, Codex `0.146.0`, Antigravity
  `1.1.10`;
- live model calls: Claude `0`, Codex `0`, Antigravity `0`.

Portable evidence v2 is recorded at:

`ai-runtime-validation/artifacts/20260803T152400Z-persistent-root-native-fork-v2/`

## Production-readiness conclusion

- Persistent Claude root: **not production-ready**. Lifecycle exists, but the
  installed CLI mapping has no qualifying live root/identity/structured-channel
  validation in this increment.
- Persistent Codex root: **not production-ready** for the same reason. The root
  command is read-only and the writer boundary is implemented, but persistent
  event return is not validated.
- Native forks live-validated in this increment: **none**. Help/discovery output
  was observed but is not Capability Registry evidence. The older Codex PoC is
  retained as historical evidence, not promoted to the stronger current
  identity/event contract.
- Structured event channel: the runtime-owned channel is implemented and
  deterministic; installed CLI integration remains **transitional/fail-closed**.
- Antigravity adaptations remaining: plan sandbox, disabled CLI log, bounded
  embedded review patch, runtime verdict enum validation, temporary/advisory
  identity, synthetic reconstruction, and human exact-head approval.
- Claude production authority still requires a disposable live contract for
  root readiness/identity, native fork/resume, persistent structured event
  return, authoritative review bound to Git-derived base/head, explicit model
  inference permission, plus soak/controlled-replacement validation. A single
  successful model response is insufficient.

## Next increment

The next increment should be **Live Persistent Adapter Contract and Durable
Async Dispatch**: validate Claude's stream/terminal integration and native
fork/resume on a disposable repository, validate a Codex app-server or other
structured persistent channel, then connect accepted terminal events to the
durable delivery/eligibility scheduler. It must keep pane parsing diagnostic
only and add operational soak coverage before enabling Claude authority.
