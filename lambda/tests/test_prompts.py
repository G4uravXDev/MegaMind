"""Tests for prompt builders and response parsers."""

from __future__ import annotations

import pytest
from prompts import commit, conflict, coverage, mentor
from prompts.conflict import InvalidModelOutputError

# --- Commit Prompt Tests ---


def test_commit_build_messages() -> None:
    payload = {
        "diff": "diff --git a/app.py b/app.py\n+print('hello')",
        "recent_commits": ["feat(core): initial setup", "docs: update readme"],
        "truncated": True,
    }
    system, messages = commit.build_messages(payload)

    assert "Conventional Commits" in system
    assert "<UNTRUSTED_DIFF>" in messages[0]["content"][0]["text"]
    assert "truncated" in messages[0]["content"][0]["text"]
    assert "feat(core): initial setup" in messages[0]["content"][0]["text"]


def test_commit_parse_response_clean() -> None:
    raw = "feat(core): add greeting endpoint\n\n- Greets the world"
    res = commit.parse_response(raw)
    assert res == {"message": "feat(core): add greeting endpoint\n\n- Greets the world"}


def test_commit_parse_response_fenced() -> None:
    raw = "```\nfix(bug): resolve race condition\n```"
    res = commit.parse_response(raw)
    assert res == {"message": "fix(bug): resolve race condition"}


def test_commit_parse_response_preamble() -> None:
    raw = "Here is the commit message:\n\nrefactor: simplify parser logic"
    res = commit.parse_response(raw)
    assert res == {"message": "refactor: simplify parser logic"}


def test_commit_parse_response_empty() -> None:
    res = commit.parse_response("   ")
    assert res == {"message": "chore: update repository files"}


# --- Conflict Prompt Tests ---


def test_conflict_build_messages() -> None:
    payload = {
        "file_path": "main.py",
        "ours": "x = 10",
        "theirs": "x = 20",
        "base": "x = 0",
        "context_before": "def run():",
        "context_after": "    return x",
    }
    system, messages = conflict.build_messages(payload)

    assert "merge conflict resolution specialist" in system
    msg_text = messages[0]["content"][0]["text"]
    assert "<UNTRUSTED_OURS>\nx = 10\n</UNTRUSTED_OURS>" in msg_text
    assert "<UNTRUSTED_THEIRS>\nx = 20\n</UNTRUSTED_THEIRS>" in msg_text
    assert "<UNTRUSTED_BASE>\nx = 0\n</UNTRUSTED_BASE>" in msg_text


def test_conflict_parse_response_valid() -> None:
    raw = '{"resolution": "x = 30", "explanation": "Merged both values"}'
    res = conflict.parse_response(raw)
    assert res == {"resolution": "x = 30", "explanation": "Merged both values"}


def test_conflict_parse_response_fenced() -> None:
    raw = """```json
{
    "resolution": "def add(a, b):\\n    return a + b",
    "explanation": "Accepted typed signature and implementation"
}
```"""
    res = conflict.parse_response(raw)
    assert res["resolution"] == "def add(a, b):\n    return a + b"
    assert "Accepted typed signature" in res["explanation"]


def test_conflict_parse_response_malformed_json() -> None:
    raw = "I resolved this by choosing ours: def foo(): pass"
    with pytest.raises(
        InvalidModelOutputError, match="Model response was not valid JSON"
    ):
        conflict.parse_response(raw)


def test_conflict_parse_response_missing_resolution_key() -> None:
    raw = '{"explanation": "Resolved successfully"}'
    with pytest.raises(
        InvalidModelOutputError, match="Missing required key 'resolution'"
    ):
        conflict.parse_response(raw)


def test_conflict_parse_response_strips_markers() -> None:
    raw = """{
    "resolution": "<<<<<<< HEAD\\nx = 10\\n=======\\nx = 20\\n>>>>>>> branch",
    "explanation": "Stripped markers"
}"""
    res = conflict.parse_response(raw)
    assert "<<<<<<<" not in res["resolution"]
    assert "=======" not in res["resolution"]
    assert ">>>>>>>" not in res["resolution"]
    assert "x = 10\nx = 20" in res["resolution"]


# --- Mentor Prompt Tests ---


def test_mentor_build_messages_with_history() -> None:
    payload = {
        "question": "How do I split my commit?",
        "repo_context": {
            "branch": "feat/mentor",
            "staged_count": 2,
            "unstaged_count": 1,
            "conflicts": False,
            "recent_commits": ["commit 1", "commit 2"],
        },
        "history": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi! How can I help with Git?"},
        ],
    }
    system, messages = mentor.build_messages(payload)

    assert "MegaMind Mentor" in system
    assert "Destructive Action Warnings" in system
    assert len(messages) == 3  # 2 history + 1 current
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"
    assert "<UNTRUSTED_QUESTION>" in messages[2]["content"][0]["text"]
    assert "feat/mentor" in messages[2]["content"][0]["text"]


def test_mentor_parse_response() -> None:
    raw = "Use `git reset HEAD~1` to uncommit changes while keeping them in your working tree."
    res = mentor.parse_response(raw)
    assert res == {"answer": raw}


# --- Coverage Prompt Tests ---


def test_coverage_build_messages() -> None:
    payload = {
        "file_path": "services/auth.py",
        "source": "def check_token(t): return bool(t)",
    }
    system, messages = coverage.build_messages(payload)

    assert "unit test suite generator" in system
    msg_text = messages[0]["content"][0]["text"]
    assert "Python (pytest)" in msg_text
    assert "<UNTRUSTED_SOURCE>" in msg_text
    assert "check_token" in msg_text


def test_coverage_parse_response_strips_fences() -> None:
    raw = """```python
import pytest

def test_check_token():
    assert True
```"""
    res = coverage.parse_response(raw)
    assert res["tests"] == "import pytest\n\ndef test_check_token():\n    assert True"
