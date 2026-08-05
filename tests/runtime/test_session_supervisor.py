from __future__ import annotations

import dataclasses
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ai_runtime.adapters import (
    AdapterCapability,
    AdapterError,
    AntigravityAdapter,
    ClaudeCLIAdapter,
    CodexCLIAdapter,
    StructuredTask,
)
from ai_runtime.adapters.cli import _SubprocessAdapter
from ai_runtime.runtime import (
    AdapterSessionContract,
    FeaturePhase,
    ForkCapability,
    ReadinessDetector,
    RuntimeConfig,
    RuntimeCoordinator,
    SessionRecoveryRequiredError,
    SessionSpec,
    SessionState,
    SessionSupervisor,
    StructuredOutputChannel,
    TerminationBehavior,
    TrustPromptBehavior,
    TurnRequest,
)

WORKER = (
    Path(__file__).resolve().parents[2] / "src" / "ai_runtime" / "runtime" / "_session_worker.py"
)


def git(repo: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments], cwd=repo, text=True, capture_output=True, check=True
    ).stdout.strip()


class SessionSupervisorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.cwd = self.root / "fixture"
        self.cwd.mkdir()
        self.supervisor = SessionSupervisor(self.root / "state")
        self.sessions: set[str] = set()

    def tearDown(self):
        for session_id in self.sessions:
            record = self.supervisor.read(session_id)
            if record and record.state != SessionState.TERMINATED:
                try:
                    self.supervisor.terminate(session_id, grace_seconds=0.1)
                except Exception:
                    if self.supervisor._live(record):
                        self.supervisor._tmux(["kill-session", "-t", record.tmux_name])
        self.temporary.cleanup()

    def spec(self, session_id="fixture-session", *, version="fixture-1", launch=None):
        self.sessions.add(session_id)
        command = launch or (
            sys.executable,
            str(WORKER),
            "--spool",
            str(self.supervisor.spool_dir / session_id),
            "--identity",
            "{session_identity}",
        )
        return SessionSpec(
            session_id=session_id,
            adapter="fixture",
            adapter_version=version,
            role="implement",
            cwd=self.cwd,
            launch_command=tuple(command),
            readiness=ReadinessDetector(r"^AI_RUNTIME_READY {session_identity}$"),
            trust_prompt=TrustPromptBehavior.NOT_APPLICABLE,
            feature_id="feature-1",
            fork=ForkCapability.SYNTHETIC,
        )

    def request(self, turn_id="turn-1", *, marker="RAW_MODEL_SENTINEL"):
        code = f"import json,sys; print(json.dumps({{'ok': True}})); print('{marker}', file=sys.stderr)"
        return TurnRequest(
            turn_id=turn_id,
            command=(sys.executable, "-c", code),
            cwd=self.cwd,
            timeout_seconds=5,
            prompt_sha256=hashlib.sha256(b"fixture prompt").hexdigest(),
            task="fixture",
        )

    def test_start_turn_acknowledge_and_terminate_state_machine(self):
        spec = self.spec()
        observation = self.supervisor.start(spec, readiness_timeout=5)
        self.assertEqual(SessionState.READY, observation.state)
        result = self.supervisor.send_turn(spec, self.request())
        self.assertEqual(SessionState.BUSY, self.supervisor.read(spec.session_id).state)
        self.assertEqual("tmux_supervised_noninteractive_v1", result.evidence["transport_mode"])
        self.assertNotIn("RAW_MODEL_SENTINEL", json.dumps(result.evidence))
        response = (
            self.supervisor._turn_dir(spec.session_id) / f"{result.turn_id}.response.json"
        ).read_text(encoding="utf-8")
        self.assertNotIn("RAW_MODEL_SENTINEL", response)
        self.assertNotIn('"stdout":', response)
        self.assertNotIn('"stderr":', response)
        self.supervisor.acknowledge_turn(spec.session_id, result.turn_id)
        self.assertEqual(SessionState.READY, self.supervisor.read(spec.session_id).state)
        self.assertEqual([], list(self.supervisor._turn_dir(spec.session_id).iterdir()))
        record = self.supervisor.terminate(spec.session_id)
        self.assertEqual(SessionState.TERMINATED, record.state)

    def test_turn_child_never_inherits_the_worker_pane_stdin(self):
        spec = self.spec("child-stdin-isolated")
        self.supervisor.start(spec, readiness_timeout=5)
        code = (
            "import json,sys; data=sys.stdin.read(); "
            "print(json.dumps({'stdin_bytes': len(data), 'stdin_isatty': sys.stdin.isatty()}))"
        )
        isolated = TurnRequest(
            turn_id="turn-stdin-isolated",
            command=(sys.executable, "-c", code),
            cwd=self.cwd,
            timeout_seconds=5,
            prompt_sha256=hashlib.sha256(b"stdin isolation").hexdigest(),
            task="fixture",
        )
        observation = self.supervisor.send_turn(spec, isolated)
        # The worker reads its TURN notices from the tmux pane. A child that
        # inherited that pane would block on a tty which never sends EOF, and
        # would race the worker for the next notice.
        self.assertFalse(observation.timed_out)
        self.assertEqual(0, observation.exit_code)
        self.assertEqual({"stdin_bytes": 0, "stdin_isatty": False}, json.loads(observation.stdout))
        self.supervisor.acknowledge_turn(spec.session_id, isolated.turn_id)
        follow = self.request("turn-after-stdin-isolated")
        recovered = self.supervisor.send_turn(spec, follow)
        self.assertFalse(recovered.timed_out)
        self.assertFalse(recovered.evidence["reconciled_completed_turn"])

    def test_runtime_restart_reattaches_live_identity(self):
        spec = self.spec("restart-live")
        self.supervisor.start(spec)
        replacement = SessionSupervisor(self.root / "state")
        report = replacement.reconcile()
        self.assertIn(spec.session_id, report.live)
        self.assertTrue(replacement.observe(spec).ready)

    def test_completed_response_is_recovered_without_resending(self):
        spec = self.spec("ack-window")
        self.supervisor.start(spec)
        counter = self.cwd / "counter.txt"
        code = (
            "import json,pathlib; p=pathlib.Path('counter.txt'); "
            "n=int(p.read_text())+1 if p.exists() else 1; p.write_text(str(n)); "
            "print(json.dumps({'count':n}))"
        )
        request = TurnRequest(
            turn_id="turn-ack-window",
            command=(sys.executable, "-c", code),
            cwd=self.cwd,
            timeout_seconds=5,
            prompt_sha256=hashlib.sha256(b"one turn").hexdigest(),
            task="fixture",
        )
        first = self.supervisor.send_turn(spec, request)
        self.assertFalse(first.evidence["reconciled_completed_turn"])
        replacement = SessionSupervisor(self.root / "state")
        report = replacement.reconcile()
        self.assertIn(spec.session_id, report.recovery_required)
        recovered = replacement.send_turn(spec, request)
        self.assertTrue(recovered.evidence["reconciled_completed_turn"])
        self.assertEqual("1", counter.read_text())
        replacement.acknowledge_turn(spec.session_id, request.turn_id)
        self.assertEqual([], list(replacement._turn_dir(spec.session_id).iterdir()))

    def test_restart_sanitizes_pre_increment_raw_response_spool(self):
        spec = self.spec("legacy-raw-spool")
        self.supervisor.start(spec)
        request = self.request("turn-legacy-raw")
        turn_dir = self.supervisor._turn_dir(spec.session_id)
        (turn_dir / f"{request.turn_id}.request.json").write_text(
            json.dumps(
                {
                    "turn_id": request.turn_id,
                    "command": list(request.command),
                    "cwd": str(request.cwd),
                    "timeout_seconds": request.timeout_seconds,
                    "prompt_sha256": request.prompt_sha256,
                    "task": request.task,
                }
            ),
            encoding="utf-8",
        )
        response = turn_dir / f"{request.turn_id}.response.json"
        response.write_text(
            json.dumps(
                {
                    "turn_id": request.turn_id,
                    "prompt_sha256": request.prompt_sha256,
                    "stdout": '{"ok": true}',
                    "stderr": "RAW_MODEL_SENTINEL",
                    "exit_code": 0,
                    "timed_out": False,
                    "duration_ms": 1,
                }
            ),
            encoding="utf-8",
        )
        replacement = SessionSupervisor(self.root / "state")
        replacement.reconcile()
        sanitized = response.read_text(encoding="utf-8")
        self.assertNotIn("RAW_MODEL_SENTINEL", sanitized)
        self.assertNotIn('"stdout":', sanitized)
        self.assertNotIn('"stderr":', sanitized)
        self.assertIn("stderr_sha256", sanitized)

    def test_missing_tmux_reconstructs_only_when_worktree_clean(self):
        clean = self.spec("clean-reconstruct")
        self.supervisor.start(clean)
        record = self.supervisor.read(clean.session_id)
        self.supervisor._tmux(["kill-session", "-t", record.tmux_name], check=True)
        recovered = self.supervisor.resume_or_reconstruct(clean, worktree_clean=True)
        self.assertTrue(recovered.ready)
        self.assertEqual(
            "synthetic_reconstruction",
            self.supervisor.read(clean.session_id).recovery_kind,
        )

        dirty = self.spec("dirty-preserved")
        self.supervisor.start(dirty)
        record = self.supervisor.read(dirty.session_id)
        self.supervisor._tmux(["kill-session", "-t", record.tmux_name], check=True)
        with self.assertRaisesRegex(SessionRecoveryRequiredError, "dirty worktree"):
            self.supervisor.resume_or_reconstruct(dirty, worktree_clean=False)
        self.assertEqual(
            SessionState.RECOVERY_REQUIRED, self.supervisor.read(dirty.session_id).state
        )

    def test_declared_resume_path_is_distinct_from_synthetic_reconstruction(self):
        spec = dataclasses.replace(self.spec("native-resume"), resume=True)
        self.supervisor.start(spec)
        record = self.supervisor.read(spec.session_id)
        self.supervisor._tmux(["kill-session", "-t", record.tmux_name], check=True)
        resume_command = (
            sys.executable,
            str(WORKER),
            "--identity",
            "{session_identity}",
            "--spool",
            str(self.supervisor.spool_dir / spec.session_id),
        )
        resumed = self.supervisor.resume_or_reconstruct(
            spec,
            worktree_clean=True,
            resume_command=resume_command,
        )
        self.assertTrue(resumed.ready)
        self.assertEqual("resume", self.supervisor.read(spec.session_id).recovery_kind)

    def test_stale_identity_and_adapter_drift_fail_closed(self):
        spec = self.spec("stale-identity")
        self.supervisor.start(spec)
        record = self.supervisor.read(spec.session_id)
        self.supervisor._tmux(
            ["set-option", "-t", record.tmux_name, "@ai_runtime_identity_sha256", "0" * 64],
            check=True,
        )
        self.assertFalse(self.supervisor.observe(spec).ready)
        self.assertEqual(
            SessionState.RECOVERY_REQUIRED, self.supervisor.read(spec.session_id).state
        )

        drift = self.spec("version-drift")
        self.supervisor.start(drift)
        with self.assertRaisesRegex(SessionRecoveryRequiredError, "adapter version"):
            self.supervisor.start(self.spec("version-drift", version="fixture-2"))

    def test_trust_prompt_and_readiness_timeout_require_recovery(self):
        trust_id = "trust-blocked"
        self.sessions.add(trust_id)
        trust = SessionSpec(
            session_id=trust_id,
            adapter="fixture",
            adapter_version="1",
            role="plan",
            cwd=self.cwd,
            launch_command=(
                sys.executable,
                "-c",
                "import time; print('Do you trust the contents', flush=True); time.sleep(5)",
            ),
            readiness=ReadinessDetector(r"NEVER_READY", trust_pattern=r"Do you trust"),
            trust_prompt=TrustPromptBehavior.REJECT,
        )
        with self.assertRaisesRegex(SessionRecoveryRequiredError, "trust prompt"):
            self.supervisor.start(trust, readiness_timeout=1)

        timeout_id = "readiness-timeout"
        self.sessions.add(timeout_id)
        timeout_spec = SessionSpec(
            session_id=timeout_id,
            adapter="fixture",
            adapter_version="1",
            role="plan",
            cwd=self.cwd,
            launch_command=(sys.executable, "-c", "import time; print('starting'); time.sleep(5)"),
            readiness=ReadinessDetector(r"NEVER_READY"),
        )
        with self.assertRaisesRegex(SessionRecoveryRequiredError, "readiness timed out"):
            self.supervisor.start(timeout_spec, readiness_timeout=0.2)

    def test_trust_prompt_is_answered_only_for_an_authorized_disposable_fixture(self):
        # Rebinding Claude's trust pattern to its real dialog makes this branch
        # reachable for the first time, so it gets its own coverage.
        launch = (
            sys.executable,
            "-c",
            "import sys,time; print('❯ 1. Yes, I trust this folder', flush=True); "  # noqa: RUF001
            "sys.stdin.readline(); print('FIXTURE_READY', flush=True); time.sleep(30)",
        )
        detector = ReadinessDetector(r"^FIXTURE_READY$", trust_pattern=r"Yes, I trust this folder")

        def trust_spec(session_id, *, disposable):
            self.sessions.add(session_id)
            return SessionSpec(
                session_id=session_id,
                adapter="fixture",
                adapter_version="1",
                role="plan",
                cwd=self.cwd,
                launch_command=launch,
                readiness=detector,
                trust_prompt=TrustPromptBehavior.ACCEPT_DISPOSABLE_ONLY,
                disposable=disposable,
            )

        authorized = self.supervisor.start(
            trust_spec("trust-disposable", disposable=True), readiness_timeout=15
        )
        self.assertEqual(SessionState.READY, authorized.state)
        with self.assertRaisesRegex(SessionRecoveryRequiredError, "authorized disposable fixture"):
            self.supervisor.start(
                trust_spec("trust-not-disposable", disposable=False), readiness_timeout=5
            )

    def test_claude_readiness_pattern_cannot_fire_on_its_own_trust_dialog(self):
        # Panes recorded verbatim from Claude 2.1.222 in a disposable fixture.
        # `_wait_ready` checks readiness against the same capture in which it
        # just answered a trust prompt, so a ready pattern that matched the
        # dialog would report READY while the dialog was still up.
        trust_pane = (
            "╭─── Claude Code v2.1.222 ───╮\n"
            "❯ 1. Yes, I trust this folder\n"  # noqa: RUF001
            "  2. No, exit\n"
        )
        idle_pane = (
            "╭─── Claude Code v2.1.222 ───╮\n"
            '❯ Try "how do I log an error?"\n'  # noqa: RUF001
            "⏸ plan mode on (shift+tab to cycle) · ← for agents\n"
        )
        version = subprocess.CompletedProcess(["claude", "--version"], 0, "2.1.222\n", "")
        with (
            mock.patch("ai_runtime.adapters.cli.shutil.which", return_value="/bin/true"),
            mock.patch("ai_runtime.adapters.cli.subprocess.run", return_value=version),
        ):
            detector = ClaudeCLIAdapter().session_contract.readiness
        self.assertTrue(re.search(detector.trust_pattern, trust_pane, re.MULTILINE))
        self.assertFalse(re.search(detector.ready_pattern, trust_pane, re.MULTILINE))
        self.assertTrue(re.search(detector.ready_pattern, idle_pane, re.MULTILINE))

    def test_termination_acknowledgement_loss_is_idempotent(self):
        spec = self.spec("terminate-ack-loss")
        self.supervisor.start(spec)
        record = self.supervisor.read(spec.session_id)
        self.supervisor._tmux(["kill-session", "-t", record.tmux_name], check=True)
        terminated = self.supervisor.terminate(spec.session_id)
        self.assertEqual(SessionState.TERMINATED, terminated.state)
        self.assertEqual(terminated, self.supervisor.terminate(spec.session_id))

    def test_vendor_profiles_declare_lifecycle_transport_contracts(self):
        version = subprocess.CompletedProcess(["tool", "--version"], 0, "fixture 1.0\n", "")
        with (
            mock.patch("ai_runtime.adapters.cli.shutil.which", return_value="/bin/true"),
            mock.patch("ai_runtime.adapters.cli.subprocess.run", return_value=version),
        ):
            agy = AntigravityAdapter()
            claude = ClaudeCLIAdapter()
            codex = CodexCLIAdapter()
            with self.assertRaisesRegex(AdapterError, "validation provenance"):
                ClaudeCLIAdapter(merge_authority=True)
            authoritative_claude = ClaudeCLIAdapter(
                merge_authority=True, authority_validation_sha256="a" * 64
            )
        self.assertFalse(claude.capability.merge_authority)
        self.assertTrue(authoritative_claude.capability.merge_authority)
        self.assertFalse(agy.capability.merge_authority)
        self.assertTrue(agy.capability.temporary)
        self.assertEqual(ForkCapability.SYNTHETIC, agy.session_contract.fork)
        self.assertEqual(ForkCapability.SYNTHETIC, claude.session_contract.fork)
        self.assertTrue(codex.capability.writes_workspace)
        self.assertIn("read-only", codex.session_contract.launch_command)
        self.assertFalse(codex.capability.native_fork)
        self.assertEqual("fail_closed", claude.persistent_declaration.structured_terminal_events)
        for adapter in (agy, claude, codex):
            self.assertTrue(adapter.session_contract.resume)
            self.assertTrue(adapter.session_contract.readiness.ready_pattern)
            self.assertIn(
                adapter.session_contract.structured_output,
                {StructuredOutputChannel.JSON_STDOUT, StructuredOutputChannel.JSONL_STDOUT},
            )


class FixtureCLIAdapter(_SubprocessAdapter):
    def __init__(self, name: str, role: StructuredTask, *, authority=False, temporary=False):
        super().__init__(binary=sys.executable)
        self._capability = AdapterCapability(
            name=name,
            version="fixture-cli-1",
            roles=frozenset({role}),
            structured_output=True,
            resume=True,
            native_fork=not temporary,
            writes_workspace=role == StructuredTask.IMPLEMENT,
            merge_authority=authority,
            temporary=temporary,
        )
        self._session_contract = AdapterSessionContract(
            launch_command=(sys.executable, "fixture"),
            readiness=ReadinessDetector(r"fixture"),
            trust_prompt=TrustPromptBehavior.NOT_APPLICABLE,
            resume=True,
            fork=ForkCapability.SYNTHETIC if temporary else ForkCapability.NATIVE,
            structured_output=StructuredOutputChannel.JSON_STDOUT,
            termination=TerminationBehavior.GRACEFUL_THEN_KILL,
        )

    @property
    def capability(self):
        return self._capability

    def _command(self, task, *, prompt, cwd, schema_path, schema_json, timeout_seconds):
        if task == StructuredTask.PLAN:
            value = {
                "summary": "fixture plan",
                "steps": ["write fixture"],
                "acceptance_criteria": ["fixture exists"],
                "risks": [],
            }
            code = f"import json,sys; print(json.dumps({value!r})); print('RAW_PANE_SENTINEL', file=sys.stderr)"
        elif task == StructuredTask.REVIEW:
            value = {"verdict": "approve", "summary": "scoped", "findings": []}
            code = f"import json,sys; print(json.dumps({value!r})); print('RAW_PANE_SENTINEL', file=sys.stderr)"
        else:
            code = (
                "import json,pathlib,subprocess,sys; "
                "pathlib.Path('hello.txt').write_text('supervised runtime\\n'); "
                "subprocess.run(['git','add','hello.txt'],check=True); "
                "subprocess.run(['git','commit','-q','-m','supervised fixture'],check=True); "
                "head=subprocess.run(['git','rev-parse','HEAD'],text=True,capture_output=True,check=True).stdout.strip(); "
                "print(json.dumps({'summary':'implemented','tests':['fixture'],'commit':head})); "
                "print('RAW_PANE_SENTINEL',file=sys.stderr)"
            )
        return [sys.executable, "-c", code]


class DirtyFailingCLIAdapter(FixtureCLIAdapter):
    def _command(self, task, *, prompt, cwd, schema_path, schema_json, timeout_seconds):
        if task != StructuredTask.IMPLEMENT:
            return super()._command(
                task,
                prompt=prompt,
                cwd=cwd,
                schema_path=schema_path,
                schema_json=schema_json,
                timeout_seconds=timeout_seconds,
            )
        code = (
            "import pathlib,sys; "
            "pathlib.Path('dirty.txt').write_text('preserve me\\n'); "
            "print('RAW_DIRTY_AGENT_OUTPUT',file=sys.stderr); sys.exit(7)"
        )
        return [sys.executable, "-c", code]


class SupervisorVerticalSliceTests(unittest.TestCase):
    def test_event_store_git_lease_review_gate_cleanup_and_privacy(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "integration"
            repo.mkdir()
            git(repo, "init", "-q", "-b", "main")
            git(repo, "config", "user.email", "runtime@example.invalid")
            git(repo, "config", "user.name", "Runtime Test")
            (repo / "README.md").write_text("fixture\n", encoding="utf-8")
            git(repo, "add", "README.md")
            git(repo, "commit", "-q", "-m", "fixture")
            planner = FixtureCLIAdapter("antigravity", StructuredTask.PLAN, temporary=True)
            implementer = FixtureCLIAdapter("codex", StructuredTask.IMPLEMENT)
            reviewer = FixtureCLIAdapter("antigravity", StructuredTask.REVIEW, temporary=True)
            runtime = RuntimeCoordinator(
                RuntimeConfig(
                    repository=repo,
                    state_dir=root / "state",
                    worktree_root=root / "worktrees",
                    allow_temporary_human_review_override=True,
                ),
                planner=planner,
                implementer=implementer,
                reviewer=reviewer,
            )
            with runtime:
                runtime.request_feature("supervised-e2e", "add fixture")
                state = runtime.run_until_gate("supervised-e2e", auto_approve_plan=True)
                self.assertEqual(FeaturePhase.AWAITING_HUMAN_APPROVAL, state.phase)
                self.assertIsNone(runtime.leases.read("supervised-e2e"))
                event_text = json.dumps(list(runtime.writer.iter_events()), sort_keys=True)
                self.assertNotIn("RAW_PANE_SENTINEL", event_text)
                self.assertIn("tmux_supervised_noninteractive_v1", event_text)
                event_count = len(list(runtime.writer.iter_events()))
                lifecycle_before = [
                    (item.session_id, item.state_revision) for item in runtime.supervisor.records()
                ]
                self.assertEqual(state, runtime.state("supervised-e2e"))
                self.assertEqual(state, runtime.state("supervised-e2e"))
                self.assertEqual(event_count, len(list(runtime.writer.iter_events())))
                self.assertEqual(
                    lifecycle_before,
                    [
                        (item.session_id, item.state_revision)
                        for item in runtime.supervisor.records()
                    ],
                )
                runtime.approve_merge(
                    "supervised-e2e",
                    expected_head=str(state.implementation["head"]),
                    approved_by="maintainer",
                )
                state = runtime.merge("supervised-e2e")
                self.assertEqual(FeaturePhase.COMPLETED, state.phase)
                self.assertEqual("supervised runtime\n", (repo / "hello.txt").read_text())
                self.assertFalse((root / "worktrees" / "supervised-e2e").exists())
                self.assertEqual("", git(repo, "status", "--porcelain"))
                records = runtime.supervisor.records()
                implementer_records = [item for item in records if item.adapter == "codex"]
                self.assertEqual(1, len(implementer_records))
                self.assertIn("worktrees/supervised-e2e", implementer_records[0].cwd)
                self.assertTrue(records)
                self.assertTrue(all(item.state == SessionState.TERMINATED for item in records))

    def test_supervised_adapter_failure_preserves_dirty_worktree_and_lease(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "integration"
            repo.mkdir()
            git(repo, "init", "-q", "-b", "main")
            git(repo, "config", "user.email", "runtime@example.invalid")
            git(repo, "config", "user.name", "Runtime Test")
            (repo / "README.md").write_text("fixture\n", encoding="utf-8")
            git(repo, "add", "README.md")
            git(repo, "commit", "-q", "-m", "fixture")
            runtime = RuntimeCoordinator(
                RuntimeConfig(
                    repository=repo,
                    state_dir=root / "state",
                    worktree_root=root / "worktrees",
                    allow_temporary_human_review_override=True,
                ),
                planner=FixtureCLIAdapter("antigravity", StructuredTask.PLAN, temporary=True),
                implementer=DirtyFailingCLIAdapter("codex", StructuredTask.IMPLEMENT),
                reviewer=FixtureCLIAdapter("antigravity", StructuredTask.REVIEW, temporary=True),
            )
            with runtime:
                runtime.request_feature("dirty-supervised", "leave recovery evidence")
                with self.assertRaisesRegex(AdapterError, "exited 7"):
                    runtime.run_until_gate("dirty-supervised", auto_approve_plan=True)
                worktree = root / "worktrees" / "dirty-supervised"
                self.assertEqual("preserve me\n", (worktree / "dirty.txt").read_text())
                self.assertIsNotNone(runtime.leases.read("dirty-supervised"))
                self.assertEqual(
                    FeaturePhase.IMPLEMENTING,
                    runtime.state("dirty-supervised").phase,
                )
                codex_record = next(
                    item for item in runtime.supervisor.records() if item.adapter == "codex"
                )
                self.assertEqual(SessionState.RECOVERY_REQUIRED, codex_record.state)
                self.assertNotIn(
                    "RAW_DIRTY_AGENT_OUTPUT",
                    (runtime.supervisor._path(codex_record.session_id)).read_text(),
                )
                self.assertEqual(
                    [],
                    list(runtime.supervisor._turn_dir(codex_record.session_id).iterdir()),
                )
                for record in runtime.supervisor.records():
                    runtime.supervisor.terminate(record.session_id, grace_seconds=0.1)


if __name__ == "__main__":
    unittest.main()
