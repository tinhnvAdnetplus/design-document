"""Conservative local Git gateway for isolated feature work."""

from __future__ import annotations

import dataclasses
import datetime as dt
import fcntl
import hashlib
import json
import os
import re
import subprocess
import uuid
from pathlib import Path


class GitCommandError(RuntimeError):
    pass


class GitInvariantError(RuntimeError):
    pass


class LeaseConflictError(GitInvariantError):
    pass


def _run(
    repo: Path, arguments: list[str], *, check: bool = True
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_EDITOR": "true",
            "GIT_SEQUENCE_EDITOR": "true",
        }
    )
    result = subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", *arguments],
        cwd=repo,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    if check and result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()[:2_048]
        raise GitCommandError(f"git {' '.join(arguments)} failed: {detail}")
    return result


def _safe_feature_id(value: str) -> str:
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}", value):
        raise ValueError("feature_id must be 1-64 safe Git/path characters")
    return value


@dataclasses.dataclass(frozen=True, slots=True)
class Workspace:
    feature_id: str
    path: Path
    branch: str
    base_ref: str
    base_head: str


@dataclasses.dataclass(frozen=True, slots=True)
class MergeBinding:
    feature_id: str
    base_head: str
    reviewed_head: str
    branch: str


@dataclasses.dataclass(frozen=True, slots=True)
class Lease:
    feature_id: str
    owner: str
    workspace: str
    fencing_token: int
    lease_id: str
    expires_at: str


class LeaseManager:
    """File-backed exclusive writer leases with monotonic fencing tokens."""

    def __init__(self, state_dir: Path):
        self.root = Path(state_dir) / "leases"
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock_path = self.root / ".lock"

    def _path(self, feature_id: str) -> Path:
        return self.root / f"{_safe_feature_id(feature_id)}.json"

    @staticmethod
    def _now() -> dt.datetime:
        return dt.datetime.now(dt.UTC)

    @staticmethod
    def _parse(value: str) -> dt.datetime:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))

    def _locked(self):
        handle = self._lock_path.open("a+", encoding="utf-8")
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        return handle

    def read(self, feature_id: str) -> Lease | None:
        path = self._path(feature_id)
        if not path.exists():
            return None
        return Lease(**json.loads(path.read_text(encoding="utf-8")))

    def acquire(
        self,
        feature_id: str,
        *,
        owner: str,
        workspace: Path,
        ttl_seconds: int = 900,
    ) -> Lease:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        with self._locked():
            current = self.read(feature_id)
            now = self._now()
            if current is not None and self._parse(current.expires_at) > now:
                if current.owner == owner and current.workspace == str(workspace.resolve()):
                    return current
                raise LeaseConflictError(
                    f"active writer lease belongs to {current.owner} (token {current.fencing_token})"
                )
            token = 1 if current is None else current.fencing_token + 1
            lease = Lease(
                feature_id=feature_id,
                owner=owner,
                workspace=str(workspace.resolve()),
                fencing_token=token,
                lease_id=uuid.uuid4().hex,
                expires_at=(now + dt.timedelta(seconds=ttl_seconds))
                .isoformat()
                .replace("+00:00", "Z"),
            )
            temporary = self._path(feature_id).with_suffix(".tmp")
            temporary.write_text(
                json.dumps(dataclasses.asdict(lease), sort_keys=True) + "\n", encoding="utf-8"
            )
            os.replace(temporary, self._path(feature_id))
            return lease

    def validate(self, lease: Lease) -> None:
        current = self.read(lease.feature_id)
        if current != lease:
            raise LeaseConflictError("writer lease was replaced or revoked")
        if self._parse(current.expires_at) <= self._now():
            raise LeaseConflictError("writer lease expired")

    def revoke(self, lease: Lease) -> None:
        with self._locked():
            current = self.read(lease.feature_id)
            if current is None:
                return
            if current.lease_id != lease.lease_id or current.fencing_token != lease.fencing_token:
                raise LeaseConflictError("cannot revoke a superseded writer lease")
            self._path(lease.feature_id).unlink()


class GitWorkspaceManager:
    def __init__(self, repository: Path, worktree_root: Path):
        self.repository = Path(repository).resolve()
        self.worktree_root = Path(worktree_root).resolve()
        if _run(self.repository, ["rev-parse", "--is-inside-work-tree"]).stdout.strip() != "true":
            raise GitInvariantError(f"not a Git worktree: {self.repository}")
        if self.worktree_root == self.repository or self.repository in self.worktree_root.parents:
            raise GitInvariantError(
                "worktree_root must not be the integration repository or its child"
            )
        self.worktree_root.mkdir(parents=True, exist_ok=True)

    def head(self, repo: Path | None = None) -> str:
        return _run(repo or self.repository, ["rev-parse", "HEAD"]).stdout.strip()

    def is_clean(self, repo: Path | None = None) -> bool:
        return not _run(repo or self.repository, ["status", "--porcelain=v1"]).stdout.strip()

    def require_clean(self, repo: Path | None = None) -> None:
        target = repo or self.repository
        if not self.is_clean(target):
            raise GitInvariantError(f"worktree is dirty and requires reconciliation: {target}")

    def ref_snapshot(self, *, excluded_branch: str | None = None) -> dict[str, str]:
        lines = _run(
            self.repository,
            [
                "for-each-ref",
                "--format=%(refname) %(objectname)",
                "refs/heads",
                "refs/tags",
            ],
        ).stdout.splitlines()
        excluded_ref = f"refs/heads/{excluded_branch}" if excluded_branch else None
        return {
            ref: object_id
            for ref, object_id in (line.split(" ", 1) for line in lines if line)
            if ref != excluded_ref
        }

    def local_config_sha256(self) -> str:
        config = _run(self.repository, ["config", "--local", "--null", "--list"]).stdout
        return hashlib.sha256(config.encode("utf-8")).hexdigest()

    def create(self, feature_id: str, *, base_ref: str = "HEAD") -> Workspace:
        safe = _safe_feature_id(feature_id)
        path = (self.worktree_root / safe).resolve()
        if path.parent != self.worktree_root:
            raise GitInvariantError("derived worktree escaped configured root")
        branch = f"ai-runtime/{safe}"
        base_head = _run(
            self.repository, ["rev-parse", "--verify", f"{base_ref}^{{commit}}"]
        ).stdout.strip()
        if path.exists():
            actual_branch = _run(path, ["branch", "--show-current"]).stdout.strip()
            if actual_branch != branch:
                raise GitInvariantError(f"existing worktree has unexpected branch: {actual_branch}")
            return Workspace(safe, path, branch, base_ref, base_head)
        branch_exists = (
            _run(
                self.repository,
                ["show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
                check=False,
            ).returncode
            == 0
        )
        arguments = ["worktree", "add"]
        if branch_exists:
            arguments.extend([str(path), branch])
        else:
            arguments.extend(["-b", branch, str(path), base_head])
        _run(self.repository, arguments)
        return Workspace(safe, path, branch, base_ref, base_head)

    def inspect_implementation(self, workspace: Workspace) -> dict[str, object]:
        self.require_clean(workspace.path)
        head = self.head(workspace.path)
        if head == workspace.base_head:
            raise GitInvariantError("implementation produced no commit")
        ancestry = _run(
            workspace.path,
            ["merge-base", "--is-ancestor", workspace.base_head, head],
            check=False,
        )
        if ancestry.returncode != 0:
            raise GitInvariantError("feature head does not descend from approved base")
        diff = _run(
            workspace.path,
            ["diff", "--binary", "--no-ext-diff", f"{workspace.base_head}..{head}"],
        ).stdout
        paths = [
            item
            for item in _run(
                workspace.path,
                ["diff", "--name-only", "--no-ext-diff", f"{workspace.base_head}..{head}"],
            ).stdout.splitlines()
            if item
        ]
        return {
            "base_head": workspace.base_head,
            "head": head,
            "branch": workspace.branch,
            "changed_paths": paths,
            "diff_sha256": hashlib.sha256(diff.encode("utf-8")).hexdigest(),
        }

    def review_patch(self, workspace: Workspace, *, max_bytes: int = 65_536) -> str:
        patch = _run(
            workspace.path,
            ["diff", "--no-ext-diff", f"{workspace.base_head}..{self.head(workspace.path)}"],
        ).stdout
        if len(patch.encode("utf-8")) > max_bytes:
            raise GitInvariantError(
                f"review patch exceeds temporary adapter limit of {max_bytes} bytes"
            )
        return patch

    def is_ancestor(self, ancestor: str, descendant: str) -> bool:
        return (
            _run(
                self.repository,
                ["merge-base", "--is-ancestor", ancestor, descendant],
                check=False,
            ).returncode
            == 0
        )

    def validate_merge(self, binding: MergeBinding) -> None:
        self.require_clean(self.repository)
        current_base = self.head()
        if current_base != binding.base_head:
            raise GitInvariantError(
                f"integration head drifted: approved {binding.base_head}, current {current_base}"
            )
        branch_head = _run(
            self.repository, ["rev-parse", "--verify", f"{binding.branch}^{{commit}}"]
        ).stdout.strip()
        if branch_head != binding.reviewed_head:
            raise GitInvariantError(
                f"reviewed head drifted: approved {binding.reviewed_head}, current {branch_head}"
            )
        preflight = _run(
            self.repository,
            ["merge-tree", "--write-tree", binding.base_head, binding.reviewed_head],
            check=False,
        )
        if preflight.returncode != 0:
            raise GitInvariantError("merge preflight found conflicts; integration was not modified")

    def merge(self, binding: MergeBinding, *, prevalidated: bool = False) -> str:
        if not prevalidated:
            self.validate_merge(binding)
        _run(
            self.repository,
            ["merge", "--no-ff", "--no-edit", binding.reviewed_head],
        )
        self.require_clean(self.repository)
        return self.head()

    def cleanup(self, workspace: Workspace, *, merged_head: str) -> None:
        if workspace.path.exists():
            self.require_clean(workspace.path)
            head = self.head(workspace.path)
            if head != merged_head:
                raise GitInvariantError("refusing cleanup because feature worktree head changed")
            _run(self.repository, ["worktree", "remove", str(workspace.path)])
        branch = _run(
            self.repository,
            ["rev-parse", "--verify", f"refs/heads/{workspace.branch}"],
            check=False,
        )
        if branch.returncode == 0:
            _run(self.repository, ["branch", "-d", workspace.branch])
