"""Tests for ApiClient."""

from __future__ import annotations

from megamind.services.api_client import ApiClient


def test_mock_mode_commit_message() -> None:
    client = ApiClient(mock=True)
    msg = client.commit_message(
        "diff --git a/test.py b/test.py\n+new", ["feat: previous"]
    )
    assert "feat: update" in msg
    assert "MEGAMIND mock" in msg


def test_mock_mode_resolve_conflict() -> None:
    client = ApiClient(mock=True)
    res = client.resolve_conflict(
        file_path="app.py",
        ours="x = 1",
        theirs="x = 2",
    )
    assert "resolution" in res
    assert "explanation" in res
    assert "Resolved by MEGAMIND Mock" in res["resolution"]


def test_mock_mode_mentor() -> None:
    client = ApiClient(mock=True)
    res = client.mentor(
        question="How to undo a commit?",
        repo_context={"branch": "main", "staged_count": 0, "unstaged_count": 0},
    )
    assert "answer" in res
    assert "MegaMind Mentor (Mock Mode)" in res["answer"]
    assert res["conversation_id"] == "mock-conv-123"


def test_mock_mode_coverage() -> None:
    client = ApiClient(mock=True)
    tests = client.coverage("utils.py", "def add(a, b): return a + b")
    assert "pytest" in tests
    assert "test_utils_basic" in tests


def test_diff_truncation() -> None:
    client = ApiClient(mock=True)
    huge_diff = "A" * 30_000
    msg = client.commit_message(huge_diff, [])
    assert "(truncated diff)" in msg
