"""Tests for conflict parser service."""

from __future__ import annotations

from megamind.services.conflict_parser import (
    apply_hunk_resolution,
    has_conflict_markers,
    parse_conflicts,
)


def test_has_conflict_markers() -> None:
    clean = "def foo():\n    return 42\n"
    assert not has_conflict_markers(clean)

    conflicted = (
        "def foo():\n"
        "<<<<<<< HEAD\n"
        "    return 1\n"
        "=======\n"
        "    return 2\n"
        ">>>>>>> branch-b\n"
    )
    assert has_conflict_markers(conflicted)


def test_parse_single_hunk() -> None:
    content = (
        "# Header\n"
        "line 1\n"
        "<<<<<<< HEAD\n"
        "feature code A\n"
        "=======\n"
        "feature code B\n"
        ">>>>>>> feature-branch\n"
        "line 2\n"
    )
    hunks = parse_conflicts(content)
    assert len(hunks) == 1
    hunk = hunks[0]
    assert hunk.index == 0
    assert hunk.ours == "feature code A"
    assert hunk.theirs == "feature code B"
    assert hunk.base == ""
    assert hunk.ours_label == "HEAD"
    assert hunk.theirs_label == "feature-branch"
    assert "line 1" in hunk.context_before
    assert "line 2" in hunk.context_after
    assert hunk.start_line == 2
    assert hunk.end_line == 6


def test_parse_diff3_hunk() -> None:
    content = (
        "<<<<<<< HEAD\n"
        "ours version\n"
        "||||||| common ancestor\n"
        "base version\n"
        "=======\n"
        "theirs version\n"
        ">>>>>>> other\n"
    )
    hunks = parse_conflicts(content)
    assert len(hunks) == 1
    hunk = hunks[0]
    assert hunk.ours == "ours version"
    assert hunk.base == "base version"
    assert hunk.theirs == "theirs version"


def test_parse_multiple_hunks() -> None:
    content = (
        "top\n"
        "<<<<<<< HEAD\n"
        "ours 1\n"
        "=======\n"
        "theirs 1\n"
        ">>>>>>> branch-1\n"
        "middle\n"
        "<<<<<<< HEAD\n"
        "ours 2\n"
        "=======\n"
        "theirs 2\n"
        ">>>>>>> branch-2\n"
        "bottom\n"
    )
    hunks = parse_conflicts(content)
    assert len(hunks) == 2
    assert hunks[0].ours == "ours 1"
    assert hunks[0].theirs == "theirs 1"
    assert hunks[1].ours == "ours 2"
    assert hunks[1].theirs == "theirs 2"


def test_parse_clean_file_no_hunks() -> None:
    content = "import os\nimport sys\n\nprint('Clean')\n"
    hunks = parse_conflicts(content)
    assert len(hunks) == 0


def test_parse_malformed_markers() -> None:
    # Missing >>>>>>>
    malformed1 = "<<<<<<< HEAD\nours without end\n=======\ntheirs without end\n"
    hunks1 = parse_conflicts(malformed1)
    assert len(hunks1) == 0

    # Missing =======
    malformed2 = "<<<<<<< HEAD\nonly ours\n>>>>>>> branch\n"
    hunks2 = parse_conflicts(malformed2)
    assert len(hunks2) == 0


def test_apply_hunk_resolution() -> None:
    content = (
        "def hello():\n"
        "<<<<<<< HEAD\n"
        "    print('Hello from Alice')\n"
        "=======\n"
        "    print('Hello from Bob')\n"
        ">>>>>>> bob\n"
        "    return True\n"
    )
    hunks = parse_conflicts(content)
    assert len(hunks) == 1

    resolved = apply_hunk_resolution(
        content,
        hunks[0],
        "    print('Hello from Alice and Bob')",
    )
    assert not has_conflict_markers(resolved)
    assert "print('Hello from Alice and Bob')" in resolved
    assert "return True" in resolved
    assert "def hello():" in resolved


def test_apply_multiple_hunk_resolutions() -> None:
    content = (
        "<<<<<<< HEAD\n"
        "part 1 ours\n"
        "=======\n"
        "part 1 theirs\n"
        ">>>>>>> b1\n"
        "between\n"
        "<<<<<<< HEAD\n"
        "part 2 ours\n"
        "=======\n"
        "part 2 theirs\n"
        ">>>>>>> b2\n"
    )
    hunks = parse_conflicts(content)
    assert len(hunks) == 2

    # Resolve first hunk
    step1 = apply_hunk_resolution(content, hunks[0], "resolved part 1")
    # Re-parse for remaining hunk
    hunks_step1 = parse_conflicts(step1)
    assert len(hunks_step1) == 1

    # Resolve second hunk
    step2 = apply_hunk_resolution(step1, hunks_step1[0], "resolved part 2")
    assert not has_conflict_markers(step2)
    assert "resolved part 1" in step2
    assert "between" in step2
    assert "resolved part 2" in step2
