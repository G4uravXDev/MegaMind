"""Git operations service wrapping GitPython."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import git
from git.exc import GitCommandError, InvalidGitRepositoryError, NoSuchPathError

from megamind.services.exceptions import (
    DestructiveActionError,
    GitServiceError,
    RepoNotFoundError,
)


@dataclass(frozen=True)
class BranchInfo:
    """Information about a local Git branch."""

    name: str
    is_current: bool
    commit_hash: str
    commit_message: str
    tracking_branch: str | None


@dataclass(frozen=True)
class CommitInfo:
    """Information about a single Git commit."""

    hash: str
    full_hash: str
    author: str
    date: str
    message: str


@dataclass(frozen=True)
class LogGraphEntry:
    """A single line from the git log graph."""

    raw_line: str
    graph: str
    commit_hash: str | None
    refs: str
    date: str
    author: str
    subject: str


@dataclass(frozen=True)
class CommitFileChange:
    """A changed file in a commit."""

    path: str
    insertions: int
    deletions: int
    change_type: str


@dataclass(frozen=True)
class CommitDetails:
    """Full details of a specific commit."""

    hash: str
    full_hash: str
    author: str
    author_email: str
    date: str
    message: str
    files: list[CommitFileChange]
    total_insertions: int
    total_deletions: int


@dataclass(frozen=True)
class StashEntry:
    """A single stash entry."""

    index: int
    message: str
    branch: str
    hash: str


@dataclass(frozen=True)
class ReflogEntry:
    """A single reflog entry."""

    selector: str
    hash: str
    action: str
    message: str


@dataclass(frozen=True)
class RepoHealth:
    """Status summary of repository health."""

    branch: str
    is_clean: bool
    is_detached: bool
    ahead: int
    behind: int
    has_remote: bool
    has_commits: bool
    has_conflicts: bool


class GitService:
    """Encapsulates all Git operations via GitPython."""

    def __init__(self, repo_path: Path | str | None = None) -> None:
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()
        try:
            self._repo = git.Repo(self.repo_path, search_parent_directories=True)
            self.repo_path = Path(self._repo.working_dir)
        except (InvalidGitRepositoryError, NoSuchPathError) as err:
            raise RepoNotFoundError(
                f"No Git repository found at {self.repo_path}"
            ) from err
        except Exception as err:
            raise GitServiceError(f"Failed to open Git repository: {err}") from err

    @property
    def repo(self) -> git.Repo:
        """Returns underlying GitPython Repo instance."""
        return self._repo

    def close(self) -> None:
        """Closes the underlying Git repository to release file handles."""
        try:
            self._repo.close()
        except OSError:
            pass

    def has_commits(self) -> bool:
        """Checks if the repository has at least one commit."""
        try:
            return self._repo.head.is_valid()
        except (ValueError, TypeError, GitCommandError):
            return False

    def is_detached(self) -> bool:
        """Returns True if HEAD is currently detached."""
        try:
            return self._repo.head.is_detached
        except (ValueError, TypeError, GitCommandError):
            return False

    def get_current_branch(self) -> str:
        """Returns active branch name or commit hash if detached."""
        try:
            if self.is_detached():
                return f"detached@{self._repo.head.commit.hexsha[:7]}"
            return self._repo.active_branch.name
        except TypeError:
            # Empty repo with uncommitted branch
            try:
                ref = self._repo.head.ref
                return ref.name
            except (ValueError, TypeError, GitCommandError):
                return "main"
        except Exception as err:
            raise GitServiceError(f"Error determining branch: {err}") from err

    def get_status_entries(self) -> dict[str, list[str]]:
        """Parses git status --porcelain=v1 into categories."""
        try:
            raw = self._repo.git.status("--porcelain=v1", "-uall")
        except GitCommandError as err:
            raise GitServiceError(f"Failed to read git status: {err}") from err

        staged: list[str] = []
        unstaged: list[str] = []
        untracked: list[str] = []
        conflicted: list[str] = []

        conflict_codes = {"UU", "AA", "UD", "DU", "DD", "AU", "UA"}

        for line in raw.splitlines():
            if not line or len(line) < 4:
                continue
            code = line[:2]
            path = line[3:].strip()
            # Handle quoted paths or renames
            if " -> " in path:
                path = path.split(" -> ")[-1]
            path = path.strip('"')

            if code in conflict_codes:
                conflicted.append(path)
                continue

            # Untracked files
            if code == "??":
                untracked.append(path)
                continue

            index_status, worktree_status = code[0], code[1]
            if index_status not in (" ", "?"):
                staged.append(path)
            if worktree_status not in (" ", "?"):
                unstaged.append(path)

        return {
            "staged": staged,
            "unstaged": unstaged,
            "untracked": untracked,
            "conflicted": conflicted,
        }

    def get_staged_files(self) -> list[str]:
        """Returns list of staged files."""
        return self.get_status_entries()["staged"]

    def get_unstaged_files(self) -> list[str]:
        """Returns list of modified unstaged files."""
        return self.get_status_entries()["unstaged"]

    def get_untracked_files(self) -> list[str]:
        """Returns list of untracked files."""
        return self.get_status_entries()["untracked"]

    def get_conflicted_files(self) -> list[str]:
        """Returns list of files with merge conflicts."""
        return self.get_status_entries()["conflicted"]

    def get_repo_health(self) -> RepoHealth:
        """Returns current health summary of repository."""
        has_comms = self.has_commits()
        branch = self.get_current_branch()
        detached = self.is_detached()
        status = self.get_status_entries()
        has_conflicts = len(status["conflicted"]) > 0
        is_clean = not (
            status["staged"]
            or status["unstaged"]
            or status["untracked"]
            or has_conflicts
        )

        ahead = 0
        behind = 0
        has_remote = False

        if has_comms and not detached:
            try:
                active = self._repo.active_branch
                tracking = active.tracking_branch()
                if tracking:
                    has_remote = True
                    ahead_commits = list(
                        self._repo.iter_commits(f"{tracking.name}..{active.name}")
                    )
                    behind_commits = list(
                        self._repo.iter_commits(f"{active.name}..{tracking.name}")
                    )
                    ahead = len(ahead_commits)
                    behind = len(behind_commits)
            except (GitCommandError, ValueError):
                # No tracking branch or remote unreachable
                pass

        return RepoHealth(
            branch=branch,
            is_clean=is_clean,
            is_detached=detached,
            ahead=ahead,
            behind=behind,
            has_remote=has_remote,
            has_commits=has_comms,
            has_conflicts=has_conflicts,
        )

    def get_recent_commits(self, limit: int = 10) -> list[CommitInfo]:
        """Returns up to `limit` recent commits."""
        if not self.has_commits():
            return []

        commits: list[CommitInfo] = []
        try:
            for c in self._repo.iter_commits(max_count=limit):
                authored_time = datetime.fromtimestamp(c.authored_date, tz=UTC)
                commits.append(
                    CommitInfo(
                        hash=c.hexsha[:7],
                        full_hash=c.hexsha,
                        author=c.author.name or "Unknown",
                        date=authored_time.strftime("%Y-%m-%d %H:%M"),
                        message=c.summary,
                    )
                )
        except Exception as err:
            raise GitServiceError(f"Failed to retrieve commits: {err}") from err

        return commits

    def get_diff(self, file_path: str | None = None) -> str:
        """Returns unstaged diff for a file or entire working directory."""
        try:
            args = []
            if file_path:
                # If file is untracked, display its content as a diff
                target = Path(self.repo_path) / file_path
                if (
                    not self.is_tracked(file_path)
                    and target.exists()
                    and not target.is_dir()
                ):
                    try:
                        content = target.read_text(encoding="utf-8", errors="replace")
                        lines = content.splitlines()
                        diff_lines = [
                            f"diff --git a/{file_path} b/{file_path}",
                            "new file mode 100644",
                            "--- /dev/null",
                            f"+++ b/{file_path}",
                            f"@@ -0,0 +1,{len(lines)} @@",
                        ]
                        for l in lines:
                            diff_lines.append(f"+{l}")
                        return "\n".join(diff_lines)
                    except (OSError, UnicodeDecodeError):
                        return f"Binary file or unreadable: {file_path}"
                args.extend(["--", file_path])
            return self._repo.git.diff(*args)
        except GitCommandError as err:
            raise GitServiceError(f"Failed to generate diff: {err}") from err

    def get_staged_diff(self, file_path: str | None = None) -> str:
        """Returns staged diff for a file or entire index."""
        try:
            args = ["--cached"]
            if file_path:
                args.extend(["--", file_path])
            return self._repo.git.diff(*args)
        except GitCommandError as err:
            raise GitServiceError(f"Failed to generate staged diff: {err}") from err

    def is_tracked(self, file_path: str) -> bool:
        """Returns True if the file is tracked in git."""
        try:
            self._repo.git.ls_files("--error-unmatch", file_path)
            return True
        except GitCommandError:
            return False

    def stage_file(self, file_path: str) -> None:
        """Stages a file."""
        try:
            self._repo.git.add("--", file_path)
        except GitCommandError as err:
            raise GitServiceError(f"Failed to stage '{file_path}': {err}") from err

    def unstage_file(self, file_path: str) -> None:
        """Unstages a file from the index."""
        try:
            if self.has_commits():
                self._repo.git.restore("--staged", "--", file_path)
            else:
                self._repo.git.rm("--cached", "-f", "--", file_path)
        except GitCommandError as err:
            raise GitServiceError(f"Failed to unstage '{file_path}': {err}") from err

    def stage_all(self) -> None:
        """Stages all changes."""
        try:
            self._repo.git.add("-A")
        except GitCommandError as err:
            raise GitServiceError(f"Failed to stage all files: {err}") from err

    def unstage_all(self) -> None:
        """Unstages all changes."""
        try:
            if self.has_commits():
                self._repo.git.restore("--staged", ".")
            else:
                self._repo.git.rm("-r", "--cached", "-f", ".")
        except GitCommandError as err:
            raise GitServiceError(f"Failed to unstage all files: {err}") from err

    def commit(self, message: str) -> str:
        """Creates a commit with the provided message."""
        if not message.strip():
            raise GitServiceError("Commit message cannot be empty")
        staged = self.get_staged_files()
        if not staged:
            raise GitServiceError("Nothing staged to commit")
        try:
            res = self._repo.git.commit("-m", message)
            return res
        except GitCommandError as err:
            raise GitServiceError(f"Failed to commit: {err}") from err

    def discard_file_changes(self, file_path: str) -> None:
        """Discards working tree changes for a file (destructive)."""
        try:
            target = Path(self.repo_path) / file_path
            if self.is_tracked(file_path):
                self._repo.git.checkout("--", file_path)
            elif target.exists():
                if target.is_file():
                    target.unlink()
                elif target.is_dir():
                    import shutil

                    shutil.rmtree(target)
        except Exception as err:
            raise GitServiceError(
                f"Failed to discard changes in '{file_path}': {err}"
            ) from err

    def restore_file(self, file_path: str) -> None:
        """Restores file from HEAD."""
        try:
            self._repo.git.checkout("HEAD", "--", file_path)
        except GitCommandError as err:
            raise GitServiceError(f"Failed to restore '{file_path}': {err}") from err

    def get_branches(self) -> list[BranchInfo]:
        """Returns list of local branches with active status and tip commit."""
        branches: list[BranchInfo] = []
        current = self.get_current_branch()
        try:
            for head in self._repo.heads:
                is_current = head.name == current
                commit_hash = head.commit.hexsha[:7] if self.has_commits() else ""
                commit_msg = head.commit.summary if self.has_commits() else ""
                tracking = head.tracking_branch()
                branches.append(
                    BranchInfo(
                        name=head.name,
                        is_current=is_current,
                        commit_hash=commit_hash,
                        commit_message=commit_msg,
                        tracking_branch=tracking.name if tracking else None,
                    )
                )
        except Exception as err:
            raise GitServiceError(f"Failed to list branches: {err}") from err
        return branches

    def create_branch(self, name: str, start_point: str | None = None) -> None:
        """Creates a new branch."""
        name = name.strip()
        if not name:
            raise GitServiceError("Branch name cannot be empty")
        try:
            self._repo.create_head(name, start_point or "HEAD")
        except GitCommandError as err:
            raise GitServiceError(f"Failed to create branch '{name}': {err}") from err

    def switch_branch(self, name: str) -> None:
        """Switches to the specified branch."""
        name = name.strip()
        if not name:
            raise GitServiceError("Branch name cannot be empty")
        try:
            self._repo.git.checkout(name)
        except GitCommandError as err:
            err_msg = str(err)
            if "overwritten by checkout" in err_msg or "local changes" in err_msg:
                raise GitServiceError(
                    f"Cannot switch to '{name}': you have uncommitted changes that would be overwritten. "
                    "Please commit, stage, or stash your changes first."
                ) from err
            raise GitServiceError(
                f"Failed to switch to branch '{name}': {err}"
            ) from err

    def rename_branch(self, old_name: str, new_name: str) -> None:
        """Renames a branch."""
        new_name = new_name.strip()
        if not new_name:
            raise GitServiceError("New branch name cannot be empty")
        try:
            self._repo.git.branch("-m", old_name, new_name)
        except GitCommandError as err:
            raise GitServiceError(
                f"Failed to rename branch '{old_name}' to '{new_name}': {err}"
            ) from err

    def delete_branch(self, name: str, force: bool = False) -> None:
        """Deletes a local branch (refuses if it is the current branch)."""
        current = self.get_current_branch()
        if name == current:
            raise DestructiveActionError(
                f"Cannot delete branch '{name}' because it is currently checked out. "
                "Switch to another branch first."
            )
        try:
            flag = "-D" if force else "-d"
            self._repo.git.branch(flag, name)
        except GitCommandError as err:
            raise GitServiceError(f"Failed to delete branch '{name}': {err}") from err

    def get_log_graph(self, max_count: int = 100) -> list[LogGraphEntry]:
        """Returns parsed log graph lines for all branches."""
        if not self.has_commits():
            return []
        try:
            raw = self._repo.git.log(
                "--graph",
                "--all",
                "--color=never",
                "--date=short",
                "--format=%h|%d|%ad|%an|%s",
                f"-n{max_count}",
            )
        except GitCommandError as err:
            raise GitServiceError(f"Failed to load git log graph: {err}") from err

        entries: list[LogGraphEntry] = []
        for line in raw.splitlines():
            if "|" in line and not line.strip().startswith("|/"):
                parts = line.split("|")
                if len(parts) >= 5:
                    prefix = parts[0].rsplit(maxsplit=1)
                    graph = prefix[0] if len(prefix) > 1 else ""
                    commit_hash = prefix[-1] if len(prefix) > 0 else ""
                    refs = parts[1].strip()
                    date = parts[2].strip()
                    author = parts[3].strip()
                    subject = "|".join(parts[4:]).strip()
                    entries.append(
                        LogGraphEntry(
                            raw_line=line,
                            graph=graph,
                            commit_hash=commit_hash,
                            refs=refs,
                            date=date,
                            author=author,
                            subject=subject,
                        )
                    )
                    continue

            # Pure graph line (e.g. "* \", "| /", "|")
            entries.append(
                LogGraphEntry(
                    raw_line=line,
                    graph=line,
                    commit_hash=None,
                    refs="",
                    date="",
                    author="",
                    subject="",
                )
            )
        return entries

    def get_commit_details(self, commit_hash: str) -> CommitDetails:
        """Retrieves full commit message, metadata, and changed files."""
        try:
            c = self._repo.commit(commit_hash)
            authored_time = datetime.fromtimestamp(c.authored_date, tz=UTC)
            stats = c.stats
            file_changes: list[CommitFileChange] = []
            for path, fstats in stats.files.items():
                file_changes.append(
                    CommitFileChange(
                        path=path,
                        insertions=fstats.get("insertions", 0),
                        deletions=fstats.get("deletions", 0),
                        change_type=fstats.get("change_type", "M"),
                    )
                )

            total = stats.total
            return CommitDetails(
                hash=c.hexsha[:7],
                full_hash=c.hexsha,
                author=c.author.name or "Unknown",
                author_email=c.author.email or "",
                date=authored_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
                message=c.message,
                files=file_changes,
                total_insertions=total.get("insertions", 0),
                total_deletions=total.get("deletions", 0),
            )
        except Exception as err:
            raise GitServiceError(
                f"Failed to inspect commit '{commit_hash}': {err}"
            ) from err

    # ── Stash operations ─────────────────────────────────────────────

    def stash_save(self, name: str) -> None:
        """Saves current working tree and index state as a named stash."""
        name = name.strip()
        if not name:
            raise GitServiceError("Stash name cannot be empty")
        try:
            res = self._repo.git.stash("push", "-m", name)
            if "No local changes to save" in res:
                raise GitServiceError("Nothing to stash: working tree is clean.")
        except GitCommandError as err:
            err_msg = str(err)
            if "No local changes to save" in err_msg:
                raise GitServiceError(
                    "Nothing to stash: working tree is clean."
                ) from err
            raise GitServiceError(f"Failed to save stash: {err}") from err

    def stash_list(self) -> list[StashEntry]:
        """Returns list of stash entries."""
        try:
            raw = self._repo.git.stash("list", "--format=%gd|%H|%gs")
        except GitCommandError as err:
            raise GitServiceError(f"Failed to list stashes: {err}") from err

        entries: list[StashEntry] = []
        for line in raw.splitlines():
            if not line.strip():
                continue
            parts = line.split("|", maxsplit=2)
            if len(parts) < 3:
                continue
            selector = parts[0].strip()
            stash_hash = parts[1].strip()
            raw_message = parts[2].strip()
            # Extract index from selector like "stash@{0}"
            try:
                idx = int(selector.split("{")[1].rstrip("}"))
            except (IndexError, ValueError):
                idx = 0
            # Extract branch from message like "On main: my message"
            branch = ""
            message = raw_message
            if raw_message.startswith("On "):
                colon_pos = raw_message.find(": ")
                if colon_pos > 0:
                    branch = raw_message[3:colon_pos]
                    message = raw_message[colon_pos + 2 :]
            # Strip "WIP on branch: " prefix if present
            if raw_message.startswith("WIP on "):
                colon_pos = raw_message.find(": ")
                if colon_pos > 0:
                    branch = raw_message[7:colon_pos]
                    message = raw_message[colon_pos + 2 :]
            entries.append(
                StashEntry(
                    index=idx,
                    message=message,
                    branch=branch,
                    hash=stash_hash[:7],
                )
            )
        return entries

    def stash_apply(self, index: int) -> None:
        """Applies a stash entry without removing it from the stash list."""
        try:
            self._repo.git.stash("apply", f"stash@{{{index}}}")
        except GitCommandError as err:
            raise GitServiceError(f"Failed to apply stash@{{{index}}}: {err}") from err

    def stash_drop(self, index: int) -> None:
        """Drops a stash entry from the stash list."""
        try:
            self._repo.git.stash("drop", f"stash@{{{index}}}")
        except GitCommandError as err:
            raise GitServiceError(f"Failed to drop stash@{{{index}}}: {err}") from err

    def stash_pop(self, index: int) -> None:
        """Applies and removes a stash entry."""
        try:
            self._repo.git.stash("pop", f"stash@{{{index}}}")
        except GitCommandError as err:
            raise GitServiceError(f"Failed to pop stash@{{{index}}}: {err}") from err

    # ── Reset operations ─────────────────────────────────────────────

    def reset(self, mode: str, target: str = "HEAD") -> None:
        """Resets HEAD to a target commit with the given mode.

        Args:
            mode: One of 'soft', 'mixed', or 'hard'.
            target: Commit reference to reset to (default: HEAD).
        """
        valid_modes = {"soft", "mixed", "hard"}
        if mode not in valid_modes:
            raise GitServiceError(
                f"Invalid reset mode '{mode}'. Must be one of: {', '.join(valid_modes)}"
            )
        try:
            self._repo.git.reset(f"--{mode}", target)
        except GitCommandError as err:
            raise GitServiceError(
                f"Failed to reset ({mode}) to '{target}': {err}"
            ) from err

    # ── Reflog operations ────────────────────────────────────────────

    def get_reflog(self, limit: int = 50) -> list[ReflogEntry]:
        """Returns recent reflog entries."""
        try:
            raw = self._repo.git.reflog(
                "--format=%gd|%H|%gs",
                f"-n{limit}",
            )
        except GitCommandError as err:
            raise GitServiceError(f"Failed to read reflog: {err}") from err

        entries: list[ReflogEntry] = []
        for line in raw.splitlines():
            if not line.strip():
                continue
            parts = line.split("|", maxsplit=2)
            if len(parts) < 3:
                continue
            selector = parts[0].strip()
            entry_hash = parts[1].strip()[:7]
            raw_msg = parts[2].strip()
            # Split action and message: "commit: Add file" -> action="commit", message="Add file"
            action = raw_msg
            message = ""
            colon_pos = raw_msg.find(": ")
            if colon_pos > 0:
                action = raw_msg[:colon_pos]
                message = raw_msg[colon_pos + 2 :]
            else:
                message = raw_msg
                action = raw_msg
            entries.append(
                ReflogEntry(
                    selector=selector,
                    hash=entry_hash,
                    action=action,
                    message=message,
                )
            )
        return entries

    def restore_to_reflog(self, selector: str) -> None:
        """Resets HEAD to the commit referenced by a reflog selector."""
        try:
            self._repo.git.reset("--hard", selector)
        except GitCommandError as err:
            raise GitServiceError(
                f"Failed to restore HEAD to '{selector}': {err}"
            ) from err
