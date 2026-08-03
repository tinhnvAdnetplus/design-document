"""Command line entry point for the minimal runtime vertical slice."""

from __future__ import annotations

import argparse
import dataclasses
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from .adapters import AntigravityAdapter, ClaudeCLIAdapter, CodexCLIAdapter
from .runtime import RuntimeConfig, RuntimeCoordinator


def _default_paths(repository: Path) -> tuple[Path, Path]:
    git_common = subprocess.run(
        ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
        cwd=repository,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    state_dir = Path(git_common) / "ai-runtime"
    worktrees = repository.parent / ".ai-runtime-worktrees" / repository.name
    return state_dir, worktrees


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="integration Git worktree")
    parser.add_argument("--state-dir", type=Path, help="runtime state (default: Git common dir)")
    parser.add_argument("--worktree-root", type=Path, help="isolated feature worktrees")
    parser.add_argument("--planner", choices=["claude", "agy"], default="claude")
    parser.add_argument("--reviewer", choices=["claude", "agy"], default="claude")
    parser.add_argument("--claude-model")
    parser.add_argument("--agy-model", default="gemini-3.6-flash-low")
    parser.add_argument("--codex-model")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument(
        "--allow-temporary-reviewer",
        action="store_true",
        help="allow an explicit human to override advisory agy review",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    request = commands.add_parser("request", help="request and run a feature to its next gate")
    request.add_argument("--feature-id", required=True)
    request.add_argument("--request", required=True)
    request.add_argument("--acceptance-criterion", action="append", default=[])
    request.add_argument("--requested-by", default="human-local")
    request.add_argument("--auto-approve-plan", action="store_true")

    run = commands.add_parser("run", help="continue a requested feature to its next gate")
    run.add_argument("--feature-id", required=True)
    run.add_argument("--auto-approve-plan", action="store_true")

    approve_plan = commands.add_parser("approve-plan", help="approve the exact durable plan")
    approve_plan.add_argument("--feature-id", required=True)
    approve_plan.add_argument("--approved-by", required=True)

    approve_merge = commands.add_parser(
        "approve-merge", help="human gate for the temporary Antigravity review profile"
    )
    approve_merge.add_argument("--feature-id", required=True)
    approve_merge.add_argument("--expected-head", required=True)
    approve_merge.add_argument("--approved-by", required=True)
    approve_merge.add_argument("--yes", action="store_true", help="confirm exact-head approval")

    merge = commands.add_parser("merge", help="run the binding-checked mechanical merge")
    merge.add_argument("--feature-id", required=True)

    reconcile = commands.add_parser(
        "reconcile-implementation", help="bind a clean commit left before event acknowledgement"
    )
    reconcile.add_argument("--feature-id", required=True)
    reconcile.add_argument("--summary", required=True)
    reconcile.add_argument("--test", action="append", default=[])
    reconcile.add_argument("--reconciled-by", required=True)

    status = commands.add_parser("status", help="replay and print one feature projection")
    status.add_argument("--feature-id", required=True)
    return parser


def _jsonable(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        return {key: _jsonable(item) for key, item in dataclasses.asdict(value).items()}
    if isinstance(value, Path):
        return str(value)
    return value


def _coordinator(args: argparse.Namespace) -> RuntimeCoordinator:
    repository = args.repo.resolve()
    default_state, default_worktrees = _default_paths(repository)
    config = RuntimeConfig(
        repository=repository,
        state_dir=(args.state_dir or default_state),
        worktree_root=(args.worktree_root or default_worktrees),
        adapter_timeout_seconds=args.timeout,
        allow_temporary_human_review_override=args.allow_temporary_reviewer,
    )
    planner = (
        ClaudeCLIAdapter(model=args.claude_model)
        if args.planner == "claude"
        else AntigravityAdapter(model=args.agy_model)
    )
    reviewer = (
        ClaudeCLIAdapter(model=args.claude_model)
        if args.reviewer == "claude"
        else AntigravityAdapter(model=args.agy_model)
    )
    return RuntimeCoordinator(
        config,
        planner=planner,
        implementer=CodexCLIAdapter(model=args.codex_model),
        reviewer=reviewer,
    )


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.command == "approve-merge" and not args.yes:
        parser.error("approve-merge requires --yes and an exact --expected-head")
    try:
        with _coordinator(args) as runtime:
            if args.command == "request":
                state = runtime.request_feature(
                    args.feature_id,
                    args.request,
                    acceptance_criteria=args.acceptance_criterion,
                    requested_by=args.requested_by,
                )
                state = runtime.run_until_gate(
                    args.feature_id, auto_approve_plan=args.auto_approve_plan
                )
            elif args.command == "run":
                state = runtime.run_until_gate(
                    args.feature_id, auto_approve_plan=args.auto_approve_plan
                )
            elif args.command == "approve-plan":
                state = runtime.approve_plan(args.feature_id, approved_by=args.approved_by)
            elif args.command == "approve-merge":
                state = runtime.approve_merge(
                    args.feature_id,
                    expected_head=args.expected_head,
                    approved_by=args.approved_by,
                )
            elif args.command == "merge":
                state = runtime.merge(args.feature_id)
            elif args.command == "reconcile-implementation":
                state = runtime.reconcile_implementation(
                    args.feature_id,
                    summary=args.summary,
                    tests=args.test,
                    reconciled_by=args.reconciled_by,
                )
            else:
                state = runtime.state(args.feature_id)
        print(json.dumps(_jsonable(state), indent=2, sort_keys=True))
        return 0
    except (RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        print(f"ai-runtime: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
