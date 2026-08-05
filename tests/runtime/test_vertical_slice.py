from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from ai_runtime.adapters import AdapterCapability, AdapterResult, StructuredTask
from ai_runtime.adapters.cli import _extract_structured
from ai_runtime.git import GitInvariantError, LeaseConflictError, LeaseManager
from ai_runtime.runtime import FeaturePhase, RuntimeConfig, RuntimeCoordinator, RuntimePolicyError
from ai_runtime.runtime.coordinator import RecoveryRequiredError


def git(repo: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments], cwd=repo, text=True, capture_output=True, check=True
    )
    return result.stdout.strip()


class ScriptedAdapter:
    def __init__(
        self,
        name: str,
        role: StructuredTask,
        value: dict,
        *,
        merge_authority: bool = False,
        temporary: bool = False,
        action=None,
        version: str = "test-1",
    ):
        self._capability = AdapterCapability(
            name=name,
            version=version,
            roles=frozenset({role}),
            structured_output=True,
            resume=False,
            native_fork=False,
            writes_workspace=role == StructuredTask.IMPLEMENT,
            merge_authority=merge_authority,
            temporary=temporary,
        )
        self.value = value
        self.action = action
        self.calls = 0

    @property
    def capability(self):
        return self._capability

    def invoke(self, task, *, prompt, cwd, schema, timeout_seconds, feature_id=None):
        self.calls += 1
        if self.action is not None:
            self.action(Path(cwd))
        value = dict(self.value)
        if task == StructuredTask.IMPLEMENT and value.get("commit") == "HEAD":
            value["commit"] = git(Path(cwd), "rev-parse", "HEAD")
        return AdapterResult(
            value=value,
            evidence={"adapter": self.capability.name, "call": self.calls},
        )


class VerticalSliceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.repo = root / "integration"
        self.state_dir = root / "state"
        self.worktrees = root / "worktrees"
        self.repo.mkdir()
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "config", "user.email", "runtime@example.invalid")
        git(self.repo, "config", "user.name", "Runtime Test")
        (self.repo / "README.md").write_text("# Fixture\n", encoding="utf-8")
        git(self.repo, "add", "README.md")
        git(self.repo, "commit", "-q", "-m", "fixture")
        self.base = git(self.repo, "rev-parse", "HEAD")

    def tearDown(self):
        self.temporary.cleanup()

    def adapters(
        self, *, authoritative=False, implementation_action=None, implementer_version="test-1"
    ):
        def default_implementation(cwd: Path):
            (cwd / "hello.txt").write_text("hello from runtime\n", encoding="utf-8")
            git(cwd, "add", "hello.txt")
            git(cwd, "commit", "-q", "-m", "implement feature")

        planner = ScriptedAdapter(
            "antigravity" if not authoritative else "claude",
            StructuredTask.PLAN,
            {
                "summary": "Add a fixture file",
                "steps": ["create hello.txt", "commit"],
                "acceptance_criteria": ["file exists"],
                "risks": [],
            },
            temporary=not authoritative,
        )
        implementer = ScriptedAdapter(
            "codex",
            StructuredTask.IMPLEMENT,
            {"summary": "Added fixture", "tests": ["test -f hello.txt"], "commit": "HEAD"},
            action=implementation_action or default_implementation,
            version=implementer_version,
        )
        reviewer = ScriptedAdapter(
            "claude" if authoritative else "antigravity",
            StructuredTask.REVIEW,
            {"verdict": "approve", "summary": "Change is scoped", "findings": []},
            merge_authority=authoritative,
            temporary=not authoritative,
        )
        return planner, implementer, reviewer

    def coordinator(self, adapters, *, allow_override=True):
        return RuntimeCoordinator(
            RuntimeConfig(
                repository=self.repo,
                state_dir=self.state_dir,
                worktree_root=self.worktrees,
                allow_temporary_human_review_override=allow_override,
            ),
            planner=adapters[0],
            implementer=adapters[1],
            reviewer=adapters[2],
        )

    def test_temporary_antigravity_requires_exact_human_gate_before_merge(self):
        adapters = self.adapters()
        with self.coordinator(adapters) as runtime:
            runtime.request_feature("feat-1", "Add hello fixture")
            state = runtime.run_until_gate("feat-1", auto_approve_plan=True)
            self.assertEqual(FeaturePhase.AWAITING_HUMAN_APPROVAL, state.phase)
            self.assertEqual(self.base, git(self.repo, "rev-parse", "HEAD"))
            self.assertIsNone(runtime.leases.read("feat-1"))
            calls = tuple(adapter.calls for adapter in adapters)
            self.assertEqual(state, runtime.state("feat-1"))
            self.assertEqual(calls, tuple(adapter.calls for adapter in adapters))

            with self.assertRaises(RuntimePolicyError):
                runtime.approve_merge("feat-1", expected_head="0" * 40, approved_by="maintainer")
            reviewed_head = str(state.implementation["head"])
            state = runtime.approve_merge(
                "feat-1", expected_head=reviewed_head, approved_by="maintainer"
            )
            self.assertEqual(FeaturePhase.APPROVED, state.phase)
            state = runtime.merge("feat-1")

            self.assertEqual(FeaturePhase.COMPLETED, state.phase)
            self.assertEqual("hello from runtime\n", (self.repo / "hello.txt").read_text())
            self.assertFalse((self.worktrees / "feat-1").exists())
            self.assertEqual("", git(self.repo, "status", "--porcelain"))
            event_types = [event["type"] for event in runtime.writer.iter_events()]
            self.assertEqual(
                [
                    "feature.requested",
                    "plan.ready",
                    "plan.approved",
                    "lease.granted",
                    "implementation.ready",
                    "lease.revoked",
                    "review.requested",
                    "implementation.progress",
                    "merge.approved",
                    "merge.started",
                    "merge.completed",
                ],
                event_types,
            )

    def test_claude_reviewer_is_authoritative_without_antigravity_override(self):
        adapters = self.adapters(authoritative=True)
        with self.coordinator(adapters, allow_override=False) as runtime:
            runtime.request_feature("feat-claude", "Add hello fixture")
            state = runtime.run_until_gate("feat-claude", auto_approve_plan=True)
            self.assertEqual(FeaturePhase.APPROVED, state.phase)
            self.assertEqual("claude_reviewer", state.approval["authority"])
            state = runtime.merge("feat-claude")
            self.assertEqual(FeaturePhase.COMPLETED, state.phase)

    def test_temporary_override_can_be_disabled(self):
        with self.coordinator(self.adapters(), allow_override=False) as runtime:
            runtime.request_feature("feat-no-override", "Add hello fixture")
            state = runtime.run_until_gate("feat-no-override", auto_approve_plan=True)
            with self.assertRaises(RuntimePolicyError):
                runtime.approve_merge(
                    "feat-no-override",
                    expected_head=str(state.implementation["head"]),
                    approved_by="maintainer",
                )

    def test_non_claude_adapter_cannot_claim_merge_authority(self):
        adapters = list(self.adapters())
        adapters[2] = ScriptedAdapter(
            "antigravity",
            StructuredTask.REVIEW,
            {"verdict": "approve", "summary": "forged", "findings": []},
            merge_authority=True,
            temporary=False,
        )
        with self.assertRaisesRegex(RuntimePolicyError, "only the non-temporary Claude"):
            self.coordinator(tuple(adapters))

    def test_committed_head_without_event_is_fenced_until_reconciled(self):
        def commit_then_fail(cwd: Path):
            (cwd / "recovered.txt").write_text("recover me\n", encoding="utf-8")
            git(cwd, "add", "recovered.txt")
            git(cwd, "commit", "-q", "-m", "commit before acknowledgement loss")
            raise RuntimeError("simulated acknowledgement loss")

        adapters = self.adapters(implementation_action=commit_then_fail)
        with self.coordinator(adapters) as runtime:
            runtime.request_feature("feat-recover", "Add recovery fixture")
            with self.assertRaisesRegex(RuntimeError, "acknowledgement loss"):
                runtime.run_until_gate("feat-recover", auto_approve_plan=True)
            self.assertEqual(FeaturePhase.IMPLEMENTING, runtime.state("feat-recover").phase)

        replacement = self.adapters()
        with self.coordinator(replacement) as runtime:
            with self.assertRaisesRegex(RecoveryRequiredError, "commit without"):
                runtime.run_until_gate("feat-recover", auto_approve_plan=True)
            self.assertEqual(0, replacement[1].calls)
            state = runtime.reconcile_implementation(
                "feat-recover",
                summary="Recovered committed change",
                tests=["manual inspection"],
                reconciled_by="maintainer",
            )
            self.assertEqual(FeaturePhase.IMPLEMENTATION_READY, state.phase)
            state = runtime.run_until_gate("feat-recover")
            self.assertEqual(FeaturePhase.AWAITING_HUMAN_APPROVAL, state.phase)

    def test_dirty_worktree_is_preserved_for_recovery(self):
        def leave_dirty(cwd: Path):
            (cwd / "dirty.txt").write_text("uncommitted\n", encoding="utf-8")

        adapters = self.adapters(implementation_action=leave_dirty)
        with self.coordinator(adapters) as runtime:
            runtime.request_feature("feat-dirty", "Leave dirty fixture")
            with self.assertRaises(GitInvariantError):
                runtime.run_until_gate("feat-dirty", auto_approve_plan=True)
            self.assertTrue((self.worktrees / "feat-dirty" / "dirty.txt").exists())
            self.assertIsNotNone(runtime.leases.read("feat-dirty"))
            self.assertEqual(FeaturePhase.IMPLEMENTING, runtime.state("feat-dirty").phase)

    def test_adapter_version_drift_blocks_restart(self):
        adapters = self.adapters()
        with self.coordinator(adapters) as runtime:
            runtime.request_feature("feat-drift", "Version binding")
        changed = self.adapters(implementer_version="test-2")
        with self.coordinator(changed) as runtime:
            with self.assertRaisesRegex(RuntimePolicyError, "adapter drift"):
                runtime.run_until_gate("feat-drift")
            self.assertEqual(0, changed[0].calls)

    def test_git_head_remains_authoritative_when_model_declares_wrong_hash(self):
        adapters = self.adapters()
        adapters[1].value["commit"] = "f" * 40
        with self.coordinator(adapters) as runtime:
            runtime.request_feature("feat-git-truth", "Add hello fixture")
            state = runtime.run_until_gate("feat-git-truth", auto_approve_plan=True)
            self.assertEqual(FeaturePhase.AWAITING_HUMAN_APPROVAL, state.phase)
            evidence = state.implementation["adapter_evidence"]
            self.assertFalse(evidence["declared_commit_matches"])
            self.assertEqual("f" * 40, evidence["declared_commit"])
            self.assertEqual(
                git(Path(state.workspace["path"]), "rev-parse", "HEAD"),
                state.implementation["head"],
            )

    def test_git_configuration_change_is_fenced(self):
        def change_config_and_commit(cwd: Path):
            (cwd / "hello.txt").write_text("hello\n", encoding="utf-8")
            git(cwd, "add", "hello.txt")
            git(cwd, "commit", "-q", "-m", "implement feature")
            git(cwd, "config", "runtime.unexpected", "true")

        adapters = self.adapters(implementation_action=change_config_and_commit)
        with self.coordinator(adapters) as runtime:
            runtime.request_feature("feat-config", "Add hello fixture")
            with self.assertRaisesRegex(RecoveryRequiredError, "Git configuration"):
                runtime.run_until_gate("feat-config", auto_approve_plan=True)
            self.assertEqual(FeaturePhase.IMPLEMENTING, runtime.state("feat-config").phase)

    def test_integration_head_drift_blocks_before_merge_started(self):
        adapters = self.adapters()
        with self.coordinator(adapters) as runtime:
            runtime.request_feature("feat-base-drift", "Add hello fixture")
            state = runtime.run_until_gate("feat-base-drift", auto_approve_plan=True)
            runtime.approve_merge(
                "feat-base-drift",
                expected_head=str(state.implementation["head"]),
                approved_by="maintainer",
            )
            (self.repo / "other.txt").write_text("integration drift\n", encoding="utf-8")
            git(self.repo, "add", "other.txt")
            git(self.repo, "commit", "-q", "-m", "advance integration")
            with self.assertRaisesRegex(GitInvariantError, "integration head drifted"):
                runtime.merge("feat-base-drift")
            self.assertEqual(FeaturePhase.APPROVED, runtime.state("feat-base-drift").phase)

    def test_restart_reconciles_merge_completed_before_event_acknowledgement(self):
        adapters = self.adapters()
        with self.coordinator(adapters) as runtime:
            runtime.request_feature("feat-merge-recover", "Add hello fixture")
            state = runtime.run_until_gate("feat-merge-recover", auto_approve_plan=True)
            runtime.approve_merge(
                "feat-merge-recover",
                expected_head=str(state.implementation["head"]),
                approved_by="maintainer",
            )
            real_merge = runtime.git.merge

            def merge_then_lose_ack(binding, *, prevalidated=False):
                real_merge(binding, prevalidated=prevalidated)
                raise RuntimeError("simulated merge acknowledgement loss")

            runtime.git.merge = merge_then_lose_ack
            with self.assertRaisesRegex(RuntimeError, "merge acknowledgement loss"):
                runtime.merge("feat-merge-recover")
            self.assertEqual(FeaturePhase.MERGING, runtime.state("feat-merge-recover").phase)
            self.assertTrue((self.repo / "hello.txt").exists())

        replacement = self.adapters()
        with self.coordinator(replacement) as runtime:
            state = runtime.merge("feat-merge-recover")
            self.assertEqual(FeaturePhase.COMPLETED, state.phase)
            self.assertTrue(state.merge["reconciled"])
            self.assertFalse((self.worktrees / "feat-merge-recover").exists())

    def test_restart_revokes_lease_after_implementation_event_acknowledgement(self):
        adapters = self.adapters()
        with self.coordinator(adapters) as runtime:
            runtime.request_feature("feat-lease-recover", "Add hello fixture")
            real_revoke = runtime.leases.revoke

            def lose_revoke_ack(lease):
                raise RuntimeError("simulated lease revoke acknowledgement loss")

            runtime.leases.revoke = lose_revoke_ack
            with self.assertRaisesRegex(RuntimeError, "lease revoke acknowledgement loss"):
                runtime.run_until_gate("feat-lease-recover", auto_approve_plan=True)
            self.assertEqual(
                FeaturePhase.IMPLEMENTATION_READY,
                runtime.state("feat-lease-recover").phase,
            )
            self.assertIsNotNone(runtime.leases.read("feat-lease-recover"))
            runtime.leases.revoke = real_revoke

        replacement = self.adapters()
        with self.coordinator(replacement) as runtime:
            state = runtime.run_until_gate("feat-lease-recover")
            self.assertEqual(FeaturePhase.AWAITING_HUMAN_APPROVAL, state.phase)
            self.assertIsNone(runtime.leases.read("feat-lease-recover"))

    def test_completed_event_retries_cleanup_idempotently(self):
        adapters = self.adapters()
        with self.coordinator(adapters) as runtime:
            runtime.request_feature("feat-cleanup-recover", "Add hello fixture")
            state = runtime.run_until_gate("feat-cleanup-recover", auto_approve_plan=True)
            runtime.approve_merge(
                "feat-cleanup-recover",
                expected_head=str(state.implementation["head"]),
                approved_by="maintainer",
            )
            real_cleanup = runtime.git.cleanup

            def lose_cleanup_ack(workspace, *, merged_head):
                raise RuntimeError("simulated cleanup acknowledgement loss")

            runtime.git.cleanup = lose_cleanup_ack
            with self.assertRaisesRegex(RuntimeError, "cleanup acknowledgement loss"):
                runtime.merge("feat-cleanup-recover")
            self.assertEqual(FeaturePhase.COMPLETED, runtime.state("feat-cleanup-recover").phase)
            self.assertTrue((self.worktrees / "feat-cleanup-recover").exists())
            runtime.git.cleanup = real_cleanup

        replacement = self.adapters()
        with self.coordinator(replacement) as runtime:
            state = runtime.merge("feat-cleanup-recover")
            self.assertEqual(FeaturePhase.COMPLETED, state.phase)
            self.assertFalse((self.worktrees / "feat-cleanup-recover").exists())

    def test_writer_lease_conflict_and_fencing(self):
        manager = LeaseManager(self.state_dir)
        first = manager.acquire("feat-lease", owner="one", workspace=self.repo, ttl_seconds=60)
        same = manager.acquire("feat-lease", owner="one", workspace=self.repo, ttl_seconds=60)
        self.assertEqual(first, same)
        with self.assertRaises(LeaseConflictError):
            manager.acquire("feat-lease", owner="two", workspace=self.repo, ttl_seconds=60)
        manager.revoke(first)
        self.assertIsNone(manager.read("feat-lease"))

    def test_adapter_parser_skips_json_schema_shape_before_structured_output(self):
        schema = {
            "properties": {
                "summary": {"type": "string"},
                "steps": {"type": "array"},
                "acceptance_criteria": {"type": "array"},
                "risks": {"type": "array"},
            },
            "summary": {"type": "string"},
            "steps": {"type": "array"},
            "acceptance_criteria": {"type": "array"},
            "risks": {"type": "array"},
        }
        expected = {
            "summary": "valid plan",
            "steps": ["one"],
            "acceptance_criteria": ["done"],
            "risks": [],
        }
        output = json.dumps({"json_schema": schema, "structured_output": expected})
        self.assertEqual(
            expected,
            _extract_structured(
                output,
                StructuredTask.PLAN,
                {"summary", "steps", "acceptance_criteria", "risks"},
            ),
        )


if __name__ == "__main__":
    unittest.main()
