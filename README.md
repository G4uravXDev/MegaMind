# ZIT – AI-Powered Terminal Git Assistant

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![TUI Framework](https://img.shields.io/badge/TUI-Textual-green.svg)](https://textual.textualize.io/)
[![Backend](https://img.shields.io/badge/backend-Django%20REST-red.svg)](https://www.django-rest-framework.org/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**ZIT** is a high-performance terminal UI (TUI) and AI-assisted Git companion designed to streamline everyday developer workflows. It brings visual clarity, safety guards, and intelligent automation directly to your terminal—from staging and conventional commits to interactive 3-panel merge conflict resolution, branch management, topology log graphs, time travel, and contextual AI mentoring.

---

## 🏗 System Architecture

```text
               ┌─────────────────────────────────────────────────────┐
               │                  ZIT Terminal (TUI)                 │
               │  (Textual · GitPython · HTTPX · Rich · Safe Modals)  │
               └──────────────┬──────────────────────┬───────────────┘
                              │                      │
                   Local Git Operations      REST API (Token Auth)
                              │                      │
                              ▼                      ▼
                     ┌────────────────┐   ┌───────────────────────────┐
                     │   Local Repo   │   │     Django REST Backend   │
                     │    (.git)      │   │ (Auth, Sessions, History) │
                     └────────────────┘   └──────────┬────────────────┘
                                                     │
                                             Proxy / Invoke
                                                     │
                                                     ▼
                                          ┌─────────────────────┐
                                          │  AI Engine / Lambda │
                                          │  (Bedrock/OpenAI/   │
                                          │   Gemini / Mock)    │
                                          └─────────────────────┘
```

The repository is structured as a modular monorepo:

- **`client/`**: Full-featured Textual TUI client. Encapsulates all Git operations inside `GitService` (pure GitPython) and all AI communications inside `ApiClient` (HTTPX). Includes non-blocking worker threads, destructive action confirmation dialogs, and an offline mock mode.
- **`backend/`**: Django REST Framework backend providing user authentication (DRF Token), session persistence, and API proxy routing.
- **`lambda/`**: Serverless AI inference functions for generating commit messages, resolving complex merge conflicts, generating unit test suites, and conversational Git mentoring.
- **`docs/`**: Technical documentation, architecture decision records, and specifications.

---

## ⚡ Key Features

| Feature | Key | Description |
|---|---|---|
| **Repository Dashboard** | `Esc` | Real-time overview of branch, working tree health (clean/dirty), ahead/behind tracking, and recent commits. |
| **Interactive Staging** | `s` | Split view with file status on the left and live syntax-colored diffs on the right. Stage (`Enter`/`Space`), stage all (`a`), unstage all (`u`), and discard (`d` with confirmation). |
| **AI Commit Workspace** | `c` | Review staged diffs. Press `g` to generate Conventional Commit messages using diff analysis + commit history. Commit with `Ctrl+S`. |
| **Branch Manager** | `b` | List branches with active indicator. Switch branches (`Enter` with collision detection), create (`n`), rename (`r`), and safely delete (`d`). |
| **Visual Log Graph** | `l` | Scrollable topological ASCII graph representing `--graph --all`. Press `Enter` to inspect full commit details and per-file `+X/-Y` diff statistics. |
| **Time Travel** | `t` | **Tab 1:** Stash save/apply/pop/drop.<br>**Tab 2:** Soft, Mixed, and Hard reset with explicit warnings.<br>**Tab 3:** Reflog history viewer and HEAD restoration. |
| **3-Panel Conflict Resolver** | `m` | 3-column view: *Ours* (left), *AI Suggestion / Manual Edit* (center), *Theirs* (right). Press `Shift+G` for AI resolution. Automatically writes clean files and stages them upon completion! |
| **AI Git Mentor** | `a` | Conversational Git assistant with real-time repo context (branch, dirty status, recent commits). Answers rendered in rich Markdown. |
| **AI Test Coverage** | `v` | Generate unit test suites for any highlighted file on Dashboard or Staging screens. Inspect code and save directly to disk (`s`). |
| **Help Cheatsheet** | `?` | Global shortcut overlay showing all keybindings across every screen. |

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.11+
- Git installed and accessible on your `PATH`

### 2. Running the Backend Server

```powershell
# Windows PowerShell
cd backend
.venv\Scripts\Activate.ps1
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

- **API Base URL:** `http://127.0.0.1:8000`
- **Admin Interface:** `http://127.0.0.1:8000/admin/` (Default admin: `admin` / `AdminPass123!`)
- **Default DRF Auth Token:** `1ab00d6ac0f622ab56b655f9cfd553dcdff28292`

---

### 3. Running the Terminal Client

#### Option A: Offline / Mock Mode (No LLM Required)
ZIT includes a built-in mock mode (`ZIT_MOCK=1`) so you can explore the complete TUI and all workflows immediately without configuring API keys:

```powershell
cd client
.venv\Scripts\Activate.ps1
$env:ZIT_MOCK="1"
python -m zit
```

You can also pass a path to any Git repository:
```powershell
python -m zit C:\path\to\your\repo
```

#### Option B: Connected to Backend
```powershell
cd client
.venv\Scripts\Activate.ps1
$env:ZIT_API_URL="http://127.0.0.1:8000"
$env:ZIT_TOKEN="1ab00d6ac0f622ab56b655f9cfd553dcdff28292"
python -m zit
```

---

## 🤖 Connecting an LLM to ZIT

To enable live AI generation (instead of mock mode), you can connect any LLM provider (OpenAI, Anthropic Claude, Google Gemini, or AWS Bedrock):

1. **Backend Integration**:
   Configure your LLM credentials in `backend/.env`:
   ```dotenv
   OPENAI_API_KEY=sk-...
   # or
   GEMINI_API_KEY=AIzaSy...
   # or
   AWS_REGION=us-east-1
   LAMBDA_FUNCTION_NAME=zit-ai
   ```

2. **Endpoints Implemented by ZIT Client**:
   The client communicates with the backend via the following REST contracts:
   - `POST /api/ai/commit-message/`: Generates a commit message from `{diff: str, recent_commits: list[str]}`.
   - `POST /api/ai/resolve-conflict/`: Resolves merge conflict from `{file_path, ours, theirs, base, context_before, context_after}`.
   - `POST /api/ai/mentor/`: Answers conversational queries from `{question: str, repo_context: dict, conversation_id: str}`.
   - `POST /api/ai/coverage/`: Generates unit tests from `{file_path: str, source: str}`.

---

## 🧪 Testing & Quality Assurance

The ZIT terminal client has an extensive test suite with **65 automated tests** covering all screens, widgets, modal flows, and Git services:

```powershell
# Run all tests
cd client
.venv\Scripts\python.exe -m pytest -v

# Run linter & formatter checks
.venv\Scripts\ruff.exe check zit tests
.venv\Scripts\ruff.exe format --check zit tests
```

---

## 🛡 Safety & Design Principles

- **No Data Loss Without Consent:** Destructive operations (`git reset --hard`, discarding local modifications, branch deletion, dropping stashes) are always gated behind an explicit `ConfirmDialog` stating what will be affected.
- **Traceback-Free Experience:** All GitPython and HTTP errors are trapped and surfaced in dismissible modal panels with human-readable diagnostic messages.
- **Non-Blocking UI:** Heavy Git diffs, network requests, and AI queries run in background worker threads with loading overlays, keeping terminal interactions fluid and responsive.
- **Cross-Platform:** Built with `pathlib` for consistent execution across Windows, macOS, and Linux.

