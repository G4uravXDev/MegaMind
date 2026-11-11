"""Tests for Milestone 8: AI Mentor Chat screen."""

from __future__ import annotations

import os

import git
import pytest

from zit.app import ZitApp
from zit.screens.dashboard import DashboardScreen
from zit.screens.mentor import MentorScreen


@pytest.mark.anyio
async def test_navigate_to_mentor(repo_with_commits: git.Repo) -> None:
    """Pressing 'a' on dashboard navigates to MentorScreen."""
    os.environ["ZIT_MOCK"] = "1"
    app = ZitApp(repo_path=repo_with_commits.working_dir)
    try:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert isinstance(app.screen, DashboardScreen)

            await pilot.press("a")
            await pilot.pause()
            assert isinstance(app.screen, MentorScreen)

            from textual.widgets import Label

            lbl = app.screen.query_one("#mentor-context-lbl", Label)
            assert "Branch:" in str(lbl.render())
    finally:
        del os.environ["ZIT_MOCK"]


@pytest.mark.anyio
async def test_mentor_chat_flow(repo_with_commits: git.Repo) -> None:
    """Submitting a question receives an AI markdown answer and updates conversation ID."""
    os.environ["ZIT_MOCK"] = "1"
    app = ZitApp(repo_path=repo_with_commits.working_dir)
    try:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("a")
            await pilot.pause()

            screen = app.screen
            assert isinstance(screen, MentorScreen)

            from textual.widgets import Markdown

            # Submit a question
            screen.submit_question("How do I undo my last commit?")

            # Wait for background worker
            for _ in range(5):
                await pilot.pause()
                if screen.query(Markdown):
                    break

            # Verify AI answer was mounted
            md_widgets = list(screen.query(Markdown))
            assert len(md_widgets) >= 1
            rendered = " ".join(str(c.render()) for c in md_widgets[0].children)
            assert "ZIT Mentor" in rendered or "undo" in rendered

            # Verify conversation_id was saved
            assert screen._conversation_id is not None
    finally:
        del os.environ["ZIT_MOCK"]


@pytest.mark.anyio
async def test_mentor_multi_turn_conversation_id(
    repo_with_commits: git.Repo,
) -> None:
    """Conversation ID is maintained across multiple conversation turns."""
    os.environ["ZIT_MOCK"] = "1"
    app = ZitApp(repo_path=repo_with_commits.working_dir)
    try:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("a")
            await pilot.pause()

            screen = app.screen
            assert isinstance(screen, MentorScreen)

            from textual.widgets import Markdown

            # Turn 1
            screen.submit_question("First question")
            for _ in range(5):
                await pilot.pause()
                if screen.query(Markdown):
                    break

            conv_id_1 = screen._conversation_id
            assert conv_id_1 is not None

            # Turn 2
            screen.submit_question("Second follow-up question")
            for _ in range(5):
                await pilot.pause()
                if len(list(screen.query(Markdown))) >= 2:
                    break

            conv_id_2 = screen._conversation_id
            assert conv_id_2 == conv_id_1
    finally:
        del os.environ["ZIT_MOCK"]


@pytest.mark.anyio
async def test_mentor_clear_chat(repo_with_commits: git.Repo) -> None:
    """Pressing 'c' clears chat history and resets conversation ID."""
    os.environ["ZIT_MOCK"] = "1"
    app = ZitApp(repo_path=repo_with_commits.working_dir)
    try:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("a")
            await pilot.pause()

            screen = app.screen
            assert isinstance(screen, MentorScreen)

            from textual.widgets import Markdown

            screen.submit_question("Something to clear")
            for _ in range(5):
                await pilot.pause()
                if screen.query(Markdown):
                    break

            assert screen._conversation_id is not None

            # Clear chat
            screen.action_clear_chat()
            await pilot.pause()

            assert screen._conversation_id is None
            assert len(list(screen.query(Markdown))) == 0
    finally:
        del os.environ["ZIT_MOCK"]


@pytest.mark.anyio
async def test_mentor_escape_returns_to_dashboard(
    repo_with_commits: git.Repo,
) -> None:
    """Pressing Esc on MentorScreen returns to dashboard."""
    os.environ["ZIT_MOCK"] = "1"
    app = ZitApp(repo_path=repo_with_commits.working_dir)
    try:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("a")
            await pilot.pause()
            assert isinstance(app.screen, MentorScreen)

            await pilot.press("escape")
            await pilot.pause()
            assert isinstance(app.screen, DashboardScreen)
    finally:
        del os.environ["ZIT_MOCK"]
