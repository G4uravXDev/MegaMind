"""Conflict parser for Git merge conflict markers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConflictHunk:
    """Represents a single conflicted section in a file."""

    index: int
    ours: str
    theirs: str
    base: str
    ours_label: str
    theirs_label: str
    context_before: str
    context_after: str
    start_line: int  # 0-based index of <<<<<<<
    end_line: int  # 0-based index of >>>>>>>


def has_conflict_markers(content: str) -> bool:
    """Returns True if the content contains git conflict markers."""
    lines = content.splitlines()
    has_start = any(line.startswith("<<<<<<<") for line in lines)
    has_sep = any(line.startswith("=======") for line in lines)
    has_end = any(line.startswith(">>>>>>>") for line in lines)
    return has_start and has_sep and has_end


def parse_conflicts(content: str, max_context: int = 20) -> list[ConflictHunk]:
    """Parses standard git and diff3 conflict markers into ConflictHunks.

    Handles:
    - 2-way conflicts: <<<<<<< / ======= / >>>>>>>
    - 3-way conflicts (diff3): <<<<<<< / ||||||| / ======= / >>>>>>>
    - Malformed or incomplete markers without raising exceptions.
    """
    lines = content.splitlines(keepends=True)
    raw_lines = [line.rstrip("\r\n") for line in lines]
    hunks: list[ConflictHunk] = []

    i = 0
    total_lines = len(raw_lines)

    while i < total_lines:
        line = raw_lines[i]
        if line.startswith("<<<<<<<"):
            start_line = i
            ours_label = line[7:].strip()
            ours_lines: list[str] = []
            base_lines: list[str] = []
            theirs_lines: list[str] = []
            theirs_label = ""

            in_ours = True
            in_base = False
            in_theirs = False
            found_end = False

            j = i + 1
            while j < total_lines:
                curr = raw_lines[j]
                if curr.startswith("|||||||"):
                    in_ours = False
                    in_base = True
                elif curr.startswith("======="):
                    in_ours = False
                    in_base = False
                    in_theirs = True
                elif curr.startswith(">>>>>>>"):
                    theirs_label = curr[7:].strip()
                    end_line = j
                    found_end = True
                    break
                else:
                    if in_ours:
                        ours_lines.append(curr)
                    elif in_base:
                        base_lines.append(curr)
                    elif in_theirs:
                        theirs_lines.append(curr)
                j += 1

            if found_end and in_theirs:
                # Valid hunk found
                # Gather context before
                ctx_before_start = max(0, start_line - max_context)
                context_before = "".join(lines[ctx_before_start:start_line])

                # Gather context after
                ctx_after_end = min(total_lines, end_line + 1 + max_context)
                context_after = "".join(lines[end_line + 1 : ctx_after_end])

                hunk = ConflictHunk(
                    index=len(hunks),
                    ours="\n".join(ours_lines),
                    theirs="\n".join(theirs_lines),
                    base="\n".join(base_lines),
                    ours_label=ours_label,
                    theirs_label=theirs_label,
                    context_before=context_before,
                    context_after=context_after,
                    start_line=start_line,
                    end_line=end_line,
                )
                hunks.append(hunk)
                i = end_line + 1
            else:
                # Malformed marker without closing >>>>>>>, advance by 1
                i += 1
        else:
            i += 1

    return hunks


def apply_hunk_resolution(content: str, hunk: ConflictHunk, resolution: str) -> str:
    """Replaces a conflict hunk with the given resolution text."""
    lines = content.splitlines(keepends=True)
    if hunk.start_line < 0 or hunk.end_line >= len(lines):
        return content

    res_lines = resolution.splitlines(keepends=True)
    if res_lines and not res_lines[-1].endswith(("\n", "\r")):
        res_lines[-1] += "\n"
    elif not res_lines and resolution != "":
        res_lines = [resolution + "\n"]

    new_lines = lines[: hunk.start_line] + res_lines + lines[hunk.end_line + 1 :]
    return "".join(new_lines)
