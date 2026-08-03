from __future__ import annotations

import dataclasses
import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from ai_runtime.events import new_event
from ai_runtime.store import EventStoreConfig, EventWriter, GroupCommitConfig, GroupCommitPolicy
from ai_runtime.runtime import (
    CapabilityRegistry,
    CapabilityUnavailableError,
    CapabilityValidation,
    FeatureSessionFactory,
    FeatureSessionRequest,
    ForkMode,
    PersistentAdapterDeclaration,
    ReadinessDetector,
    SessionRecoveryRequiredError,
    SessionState,
    SessionSupervisor,
    TerminalEventIntent,
    TrustPromptBehavior,
)


WORKER = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "ai_runtime"
    / "runtime"
    / "_terminal_event_worker.py"
)
PROVENANCE = "a" * 64


def git(repo: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments], cwd=repo, text=True, capture_output=True, check=True
    ).stdout.strip()


def worker_command() -> tuple[str, ...]:
    return (
        sys.executable,
        str(WORKER),
        "--state-dir",
        "{state_dir}",
        "--session-id",
        "{session_id}",
        "--identity",
        "{session_identity}",
    )


def declaration(
    adapter: str = "claude",
    *,
    roles=frozenset({"planner", "reviewer"}),
    native=CapabilityValidation.VALIDATED,
    root=CapabilityValidation.VALIDATED,
    channel=CapabilityValidation.VALIDATED,
    resume=CapabilityValidation.FAIL_CLOSED,
    resume_command=None,
    revision="fixture-persistent-v1",
    writes=False,
    temporary=False,
    merge=False,
) -> PersistentAdapterDeclaration:
    return PersistentAdapterDeclaration(
        adapter=adapter,
        adapter_version=f"{adapter}-fixture-1",
        declaration_revision=revision,
        roles=roles,
        root_launch_command=worker_command(),
        root_readiness=ReadinessDetector(r"^AI_RUNTIME_EVENT_READY {session_identity}$"),
        synthetic_launch_command=worker_command(),
        native_fork_command=worker_command() if native == CapabilityValidation.VALIDATED else None,
        resume_command=resume_command,
        persistent_root=root,
        native_fork=native,
        resume=resume,
        structured_terminal_events=channel,
        validation_provenance_sha256=(
            PROVENANCE
            if CapabilityValidation.VALIDATED in {native, root, channel, resume}
            else None
        ),
        writes_workspace=writes,
        merge_authority=merge,
        temporary=temporary,
        trust_prompt=TrustPromptBehavior.NOT_APPLICABLE,
    )


class FeatureSessionFactoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.repo = self.base / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "config", "user.email", "fixture@example.invalid")
        git(self.repo, "config", "user.name", "Fixture")
        (self.repo / "README.md").write_text("fixture\n", encoding="utf-8")
        git(self.repo, "add", "README.md")
        git(self.repo, "commit", "-q", "-m", "fixture")
        self.state = self.base / "state"
        self.supervisor = SessionSupervisor(self.state)
        self.capabilities = CapabilityRegistry()
        self.capabilities.register(declaration())
        self.factory = FeatureSessionFactory(
            self.supervisor,
            repository=self.repo,
            policy_revision="policy-fixture-1",
            capabilities=self.capabilities,
        )
        self.factory.provision_root("claude", readiness_timeout=5)

    def tearDown(self):
        for record in self.supervisor.records():
            if record.state != SessionState.TERMINATED:
                try:
                    self.supervisor.terminate(record.session_id, grace_seconds=0.1)
                except Exception:
                    if self.supervisor._live(record):
                        self.supervisor._tmux(["kill-session", "-t", record.tmux_name])
        self.temporary.cleanup()

    def request(self, feature="feat-1", role="planner", attempt=1, **kwargs):
        return FeatureSessionRequest(
            adapter=kwargs.pop("adapter", "claude"),
            feature_id=feature,
            role=role,
            attempt=attempt,
            cwd=kwargs.pop("cwd", self.repo),
            git_base=kwargs.pop("git_base", git(self.repo, "rev-parse", "HEAD")),
            reconstruction_provenance_sha256=kwargs.pop(
                "reconstruction_provenance_sha256", PROVENANCE
            ),
            **kwargs,
        )

    def wait_result(self, intent, factory=None):
        target = factory or self.factory

        def validate(value):
            if value.get("kind") != "fixture.completed":
                raise ValueError("invalid fixture event")

        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            result = target.collect_structured_event(intent, validator=validate)
            if result is not None:
                return result
            time.sleep(0.05)
        self.fail("structured result was not produced")

    def test_root_lives_across_native_features_and_cleanup_does_not_kill_it(self):
        root = self.factory.root("claude")
        first = self.request("feat-one")
        self.factory.create_from_root(first, readiness_timeout=5)
        child_one = self.supervisor.read("claude-feature-feat-one-planner-1")
        self.assertEqual(str(ForkMode.NATIVE), child_one.fork_mode)
        self.factory.terminate(child_one.session_id, grace_seconds=0.1)
        self.assertTrue(self.factory.observe(root.session_id).ready)

        second = self.request("feat-two")
        self.factory.create_from_root(second, readiness_timeout=5)
        child_two = self.supervisor.read("claude-feature-feat-two-planner-1")
        self.assertEqual(root.session_id, child_two.parent_root_id)
        self.assertEqual(SessionState.READY, self.supervisor.read(root.session_id).state)

    def test_runtime_restart_reattaches_root_and_child(self):
        request = self.request("restart-child")
        self.factory.create_from_root(request, readiness_timeout=5)
        replacement_supervisor = SessionSupervisor(self.state)
        replacement_registry = CapabilityRegistry()
        replacement_registry.register(declaration())
        replacement = FeatureSessionFactory(
            replacement_supervisor,
            repository=self.repo,
            policy_revision="policy-fixture-1",
            capabilities=replacement_registry,
        )
        report = replacement.reconcile()
        self.assertIn("claude-root", report.roots)
        self.assertIn("claude-feature-restart-child-planner-1", report.features)
        self.assertTrue(replacement.observe("claude-root").ready)
        self.assertTrue(replacement.observe("claude-feature-restart-child-planner-1").ready)

    def test_lost_root_reconstruction_and_lost_resume_id_select_reconstruction(self):
        root = self.factory.root("claude")
        self.supervisor._tmux(["kill-session", "-t", root.tmux_name], check=True)
        observed = self.factory.resume_or_reconstruct(root.session_id, worktree_clean=True)
        self.assertTrue(observed.ready)
        self.assertEqual(
            "synthetic_reconstruction", self.supervisor.read(root.session_id).recovery_kind
        )

        self.factory.create_from_root(self.request("resume-missing"), readiness_timeout=5)
        child = self.supervisor.read("claude-feature-resume-missing-planner-1")
        self.supervisor._tmux(["kill-session", "-t", child.tmux_name], check=True)
        recovered = self.factory.resume_or_reconstruct(child.session_id, worktree_clean=True)
        self.assertTrue(recovered.ready)
        self.assertEqual(
            "synthetic_reconstruction", self.supervisor.read(child.session_id).recovery_kind
        )

    def test_synthetic_fork_is_explicit_and_feature_attempt_cannot_be_reused(self):
        request = self.request("synthetic")
        self.factory.synthetic_fork(request, readiness_timeout=5)
        record = self.supervisor.read("claude-feature-synthetic-planner-1")
        self.assertEqual(str(ForkMode.SYNTHETIC), record.fork_mode)
        self.assertEqual(PROVENANCE, record.reconstruction_sha256)
        with self.assertRaisesRegex(SessionRecoveryRequiredError, "never reusable"):
            self.factory.synthetic_fork(request, readiness_timeout=5)

    def test_event_intent_precedes_fixed_notice_and_ack_recovery_does_not_resend(self):
        self.factory.create_from_root(self.request("events"), readiness_timeout=5)
        session_id = "claude-feature-events-planner-1"
        intent = self.factory.deliver_event_reference(
            session_id,
            event_reference="evt-fixture-1",
            reference_id="ref-fixture-1",
            packet={
                "prompt": "private fixture prompt",
                "structured_event": {"kind": "fixture.completed", "value": 1},
            },
        )
        delivery = self.state / "terminal-events" / session_id / "ref-fixture-1.delivery.json"
        inbox = self.state / "terminal-events" / session_id / "inbox" / "ref-fixture-1.json"
        self.assertTrue(inbox.exists())
        self.assertTrue(delivery.exists())
        pane = self.supervisor._capture(self.supervisor.read(session_id), 80)
        self.assertNotIn("private fixture prompt", pane)
        result = self.wait_result(intent)

        replacement_supervisor = SessionSupervisor(self.state)
        replacement_registry = CapabilityRegistry()
        replacement_registry.register(declaration())
        replacement = FeatureSessionFactory(
            replacement_supervisor,
            repository=self.repo,
            policy_revision="policy-fixture-1",
            capabilities=replacement_registry,
        )
        report = replacement.reconcile()
        self.assertIn(session_id, report.completed_unacknowledged)
        recovered = self.wait_result(intent, replacement)
        self.assertEqual(result.event, recovered.event)
        replacement.acknowledge_structured_event(intent, accepted_event_id="evt-result-1")
        replacement.acknowledge_structured_event(intent, accepted_event_id="evt-result-1")
        self.assertFalse(inbox.exists())
        self.assertEqual((), replacement.channel.pending_results(session_id))

    def test_event_store_ack_loss_is_reconciled_and_replay_has_no_side_effects(self):
        self.factory.create_from_root(self.request("event-store"), readiness_timeout=5)
        session_id = "claude-feature-event-store-planner-1"
        event = new_event(
            event_type="implementation.progress",
            feature_id="event-store",
            sequence=1,
            producer={
                "session_id": session_id,
                "role": "planner",
                "adapter": "claude",
                "adapter_version": "claude-fixture-1",
            },
            payload={"stage": "fixture"},
            correlation_id="cor-event-store",
            causation_id=None,
            policy_revision="policy-fixture-1",
            idempotency_key="event-store/result/1",
            event_id="evt-event-store-result",
        )
        intent = self.factory.deliver_event_reference(
            session_id,
            event_reference="evt-assignment",
            reference_id="ref-event-store",
            packet={"structured_event": event},
        )
        outbox = self.state / "terminal-events" / session_id / "outbox" / f"{intent.reference_id}.json"
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not outbox.exists():
            time.sleep(0.05)
        self.assertTrue(outbox.exists())
        config = EventStoreConfig(self.state / "events.db")
        with EventWriter(
            config,
            GroupCommitConfig(policy=GroupCommitPolicy.IMMEDIATE, max_batch_size=1),
        ) as writer:
            with mock.patch.object(
                self.factory,
                "acknowledge_structured_event",
                side_effect=RuntimeError("simulated event acknowledgement loss"),
            ):
                with self.assertRaisesRegex(RuntimeError, "acknowledgement loss"):
                    self.factory.accept_structured_event(
                        intent, writer=writer, validator=lambda value: None
                    )
            self.assertEqual(
                ["evt-event-store-result"],
                [item["event_id"] for item in writer.iter_events()],
            )
            with mock.patch.object(self.supervisor, "_tmux") as terminal:
                self.assertEqual(
                    1,
                    writer.replay(
                        lambda count, _event: count + 1,
                        0,
                        aggregate_stream="feature/event-store",
                    ),
                )
                terminal.assert_not_called()

        replacement = FeatureSessionFactory(
            SessionSupervisor(self.state),
            repository=self.repo,
            policy_revision="policy-fixture-1",
            capabilities=self.capabilities,
        )
        report = replacement.reconcile(
            acknowledged_event_ids=frozenset({"evt-event-store-result"})
        )
        self.assertNotIn(session_id, report.completed_unacknowledged)
        self.assertEqual((), replacement.channel.pending_results(session_id))

    def test_invalid_output_is_deleted_with_non_content_diagnostic_only(self):
        self.factory.create_from_root(self.request("invalid"), readiness_timeout=5)
        session_id = "claude-feature-invalid-planner-1"
        intent = self.factory.channel.persist_intent(
            session_id=session_id,
            event_reference="evt-invalid",
            packet={"structured_event": {"kind": "fixture.completed"}},
            reference_id="ref-invalid",
        )
        outbox = self.state / "terminal-events" / session_id / "outbox" / "ref-invalid.json"
        outbox.write_text("RAW_MODEL_SENTINEL not-json", encoding="utf-8")
        with self.assertRaisesRegex(SessionRecoveryRequiredError, "discarded"):
            self.factory.collect_structured_event(intent, validator=lambda value: None)
        self.assertFalse(outbox.exists())
        diagnostic = (
            self.state
            / "terminal-events"
            / session_id
            / "diagnostics"
            / "ref-invalid.json"
        ).read_text(encoding="utf-8")
        self.assertNotIn("RAW_MODEL_SENTINEL", diagnostic)
        self.assertIn("raw_sha256", diagnostic)
        self.assertIn("raw_bytes", diagnostic)

    def test_capability_policy_drift_fails_closed_and_profiles_do_not_remap(self):
        self.factory.create_from_root(self.request("drift"), readiness_timeout=5)
        changed = CapabilityRegistry()
        changed.register(declaration(revision="fixture-persistent-v2"))
        replacement = FeatureSessionFactory(
            SessionSupervisor(self.state),
            repository=self.repo,
            policy_revision="policy-fixture-2",
            capabilities=changed,
        )
        report = replacement.reconcile()
        self.assertIn("claude-root", report.recovery_required)
        self.assertIn("claude-feature-drift-planner-1", report.recovery_required)

    def test_root_replacement_preserves_live_child_and_records_orphaned_parent(self):
        self.factory.create_from_root(self.request("root-replace"), readiness_timeout=5)
        child_id = "claude-feature-root-replace-planner-1"
        old_root = self.factory.root("claude")
        self.factory.replace_root("claude", reason="fixture maintenance", readiness_timeout=5)
        self.assertEqual(SessionState.TERMINATED, self.supervisor.read(old_root.session_id).state)
        self.assertTrue(self.factory.observe(child_id).ready)
        report = self.factory.reconcile()
        self.assertIn(child_id, report.orphaned_parent)
        self.assertEqual("claude-root-r2", self.factory.root("claude").session_id)

    def test_native_fork_success_without_verified_readiness_fails_closed(self):
        bad_registry = CapabilityRegistry()
        bad = declaration(adapter="fixturebad", roles=frozenset({"planner"}))
        bad_command = (
            sys.executable,
            "-c",
            "import time; print('AI_RUNTIME_EVENT_READY wrong',flush=True); time.sleep(2)",
        )
        bad_registry.register(dataclasses.replace(bad, native_fork_command=bad_command))
        factory = FeatureSessionFactory(
            self.supervisor,
            repository=self.repo,
            policy_revision="policy-fixture-1",
            capabilities=bad_registry,
        )
        factory.provision_root("fixturebad", readiness_timeout=5)
        request = FeatureSessionRequest(
            adapter="fixturebad",
            feature_id="bad-native",
            role="planner",
            attempt=1,
            cwd=self.repo,
            git_base=git(self.repo, "rev-parse", "HEAD"),
            reconstruction_provenance_sha256=PROVENANCE,
        )
        with self.assertRaisesRegex(SessionRecoveryRequiredError, "verified readiness"):
            factory.native_fork(request, readiness_timeout=0.2)
        self.assertEqual(
            SessionState.RECOVERY_REQUIRED,
            self.supervisor.read("fixturebad-feature-bad-native-planner-1").state,
        )

    def test_failed_validated_resume_falls_back_to_synthetic_reconstruction(self):
        resume_registry = CapabilityRegistry()
        resume_registry.register(
            declaration(
                adapter="resumer",
                roles=frozenset({"planner"}),
                native=CapabilityValidation.FAIL_CLOSED,
                resume=CapabilityValidation.VALIDATED,
                resume_command=(sys.executable, "-c", "raise SystemExit(3)"),
            )
        )
        factory = FeatureSessionFactory(
            self.supervisor,
            repository=self.repo,
            policy_revision="policy-fixture-1",
            capabilities=resume_registry,
        )
        factory.provision_root("resumer", readiness_timeout=5)
        request = FeatureSessionRequest(
            adapter="resumer",
            feature_id="resume-fallback",
            role="planner",
            attempt=1,
            cwd=self.repo,
            git_base=git(self.repo, "rev-parse", "HEAD"),
            reconstruction_provenance_sha256=PROVENANCE,
            resume_reference_sha256="b" * 64,
        )
        factory.create_from_root(request, readiness_timeout=5)
        record = self.supervisor.read("resumer-feature-resume-fallback-planner-1")
        self.supervisor._tmux(["kill-session", "-t", record.tmux_name], check=True)
        observed = factory.resume_or_reconstruct(
            record.session_id, worktree_clean=True, readiness_timeout=1
        )
        recovered = self.supervisor.read(record.session_id)
        self.assertTrue(observed.ready)
        self.assertEqual(str(ForkMode.SYNTHETIC), recovered.fork_mode)
        self.assertEqual("synthetic_reconstruction", recovered.recovery_kind)

    def test_fail_closed_capabilities_and_authority_contract(self):
        blocked = CapabilityRegistry()
        blocked.register(
            declaration(
                root=CapabilityValidation.FAIL_CLOSED,
                native=CapabilityValidation.FAIL_CLOSED,
                channel=CapabilityValidation.FAIL_CLOSED,
            )
        )
        factory = FeatureSessionFactory(
            SessionSupervisor(self.base / "blocked-state"),
            repository=self.repo,
            policy_revision="policy-fixture-1",
            capabilities=blocked,
        )
        with self.assertRaisesRegex(CapabilityUnavailableError, "fail-closed"):
            factory.provision_root("claude")
        with self.assertRaises(ValueError):
            declaration(adapter="codex", roles=frozenset({"implementer"}), merge=True)
        with self.assertRaises(ValueError):
            declaration(
                adapter="antigravity",
                roles=frozenset({"planner", "reviewer"}),
                temporary=True,
                native=CapabilityValidation.VALIDATED,
            )

    def test_codex_writer_is_bound_to_generated_feature_worktree_and_dirty_is_preserved(self):
        codex_registry = CapabilityRegistry()
        codex_registry.register(
            declaration(
                adapter="codex",
                roles=frozenset({"implementer"}),
                writes=True,
            )
        )
        codex = FeatureSessionFactory(
            self.supervisor,
            repository=self.repo,
            policy_revision="policy-fixture-1",
            capabilities=codex_registry,
            worktree_root=self.base / "worktrees",
        )
        codex.provision_root("codex", readiness_timeout=5)
        with self.assertRaisesRegex(SessionRecoveryRequiredError, "integration worktree"):
            codex.create_from_root(
                self.request(
                    "bad-writer",
                    "implementer",
                    adapter="codex",
                    cwd=self.repo,
                    worktree_binding=self.repo,
                )
            )
        worktree = self.base / "worktrees" / "dirty-writer"
        worktree.mkdir(parents=True)
        request = self.request(
            "dirty-writer",
            "implementer",
            adapter="codex",
            cwd=worktree,
            worktree_binding=worktree,
        )
        codex.create_from_root(request, readiness_timeout=5)
        record = self.supervisor.read("codex-feature-dirty-writer-implementer-1")
        (worktree / "dirty.txt").write_text("preserve\n", encoding="utf-8")
        self.supervisor._tmux(["kill-session", "-t", record.tmux_name], check=True)
        with self.assertRaisesRegex(SessionRecoveryRequiredError, "dirty worktree"):
            codex.resume_or_reconstruct(record.session_id, worktree_clean=False)
        self.assertEqual("preserve\n", (worktree / "dirty.txt").read_text())


if __name__ == "__main__":
    unittest.main()
