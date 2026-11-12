# MEGAMIND – Terminal AI Git Assistant

**MEGAMIND** is a high-performance terminal UI (TUI) and AI-assisted Git companion built with **Textual** and **GitPython**. It streamlines everyday Git workflows—from staging and committing to complex operations like interactive 3-panel merge conflict resolution, branch management, visual log exploration, time travel, and contextual AI mentoring.

---

## 🛠 Stack

- **Runtime:** Python 3.11+
- **Terminal UI (TUI):** Textual
- **Git Operations:** GitPython
- **Networking:** HTTPX (REST calls with token authentication)
- **Terminal Rendering:** Rich
- **Code Quality & Testing:** Pytest, AnyIO, Ruff
- **Target OS:** Windows (PowerShell/CMD), macOS, Linux (cross-platform using `pathlib`)

---

## 🚀 Quick Start

### 1. Prerequisites & Environment Setup

Navigate to the `client/` directory and activate the virtual environment:

```powershell
# Windows PowerShell
cd client
.venv\Scripts\Activate.ps1
```

```bash
# macOS / Linux
cd client
source .venv/bin/activate
```

Install dependencies if setting up a fresh environment:

```bash
pip install -r requirements.txt
```

### 2. Environment Variables

Configure your environment before launching:

| Variable | Description | Default |
|---|---|---|
| `MEGAMIND_API_URL` | Base URL of the MEGAMIND backend server | `http://127.0.0.1:8000` |
| `MEGAMIND_TOKEN` | Django REST Framework authentication token | *(empty)* |
| `MEGAMIND_MOCK` | Enable offline mock mode (returns canned AI responses) | `0` (set to `1` for offline) |

To run completely offline without the Django backend:

```powershell
$env:MEGAMIND_MOCK="1"
python -m megamind
```

To run with backend authentication:

```powershell
$env:MEGAMIND_API_URL="http://127.0.0.1:8000"
$env:MEGAMIND_TOKEN="<your-drf-token>"
python -m megamind
```

---

## ⌨️ Features & Keybinding Reference

Press **`?`** anywhere in MEGAMIND to open the instant in-app cheatsheet.

### 🌐 Global Shortcuts
- **`?` / `F1`** — Open Help cheatsheet overlay
- **`Esc`** — Return to the Dashboard or dismiss the active modal
- **`r`** — Refresh data on the current screen
- **`q`** — Quit MEGAMIND

---

### 1. 📊 Dashboard (Home)
Shows current branch, working tree health (clean/dirty, conflicts), sync tracking (ahead/behind remote), and recent commit history.
- **`s`** — Staging view
- **`c`** — Commit workspace
- **`b`** — Branch manager
- **`l`** — Log graph viewer
- **`t`** — Time travel (stash, reset, recovery)
- **`m`** — Merge conflict resolver *(only enabled when conflicts exist)*
- **`a`** — AI Mentor chat
- **`v`** — Generate unit test coverage for selected file

---

### 2. 📁 Staging Screen (`s`)
Interactive staging manager with live syntax-colored diff preview.
- **`Enter` / `Space`** — Toggle stage/unstage for the highlighted file
- **`a`** — Stage all changes (`git add -A`)
- **`u`** — Unstage all changes (`git restore --staged .`)
- **`d`** — Discard file changes *(destructive; protected by `ConfirmDialog`)*
- **`c`** — Proceed directly to Commit screen
- **`v`** — Generate AI test coverage for highlighted file

---

### 3. 💾 Commit Workspace (`c`)
Review staged files and compose commit messages with AI assistance.
- **`g`** — Generate commit message via AI using the staged diff and last 10 commit messages
- **`Ctrl+S`** — Create commit *(validates non-empty message and non-empty staged index)*
- **`s`** — Switch back to Staging view

---

### 4. 🌿 Branches Manager (`b`)
List local branches, identify the currently checked-out branch, and manage branches safely.
- **`Enter`** — Switch to highlighted branch *(detects and guards uncommitted change collisions)*
- **`n`** — Create a new branch from HEAD (prompts via `InputDialog`)
- **`r`** — Rename highlighted branch (prompts via `InputDialog`)
- **`d`** — Delete highlighted branch *(protected by `ConfirmDialog`; refuses current branch)*

---

### 5. 📜 Visual Log Graph (`l`)
Scrollable commit graph visualizer representing `--graph --all` topology.
- **`↑ / ↓`** — Browse visual commit graph
- **`Enter`** — Inspect full commit metadata, author, date, message, and per-file `+X/-Y` diff statistics

---

### 6. ⏰ Time Travel (`t`)
Three dedicated tabs for repository state manipulation:
- **`1` Stashes:**
  - **`s`** — Save stash with a custom name (`InputDialog`)
  - **`a`** — Apply selected stash (keeps in list)
  - **`p`** — Pop selected stash (applies and removes)
  - **`d`** — Drop selected stash *(destructive confirmation)*
- **`2` Reset:**
  - Select between **Soft**, **Mixed**, and **Hard** reset with detailed explanations of lost/preserved state.
- **`3` Recovery (Reflog):**
  - Browse full reflog history; press **`Enter`** to restore HEAD to any previous commit point after confirmation.

---

### 7. ⚡ Merge Conflict Resolver (`m`)
Three-panel interactive merge conflict resolver:
- **Left Panel (Ours):** Local changes with branch/commit labels
- **Center Panel (AI Resolution / Manual Edit):** Editable `TextArea` pre-filled or populated by AI
- **Right Panel (Theirs):** Incoming remote/feature changes
- **`Shift+G`** — Request AI resolution for current hunk (includes 20 lines of surrounding context)
- **`m`** — Apply center panel suggestion/edit to the current hunk
- **`n` / `p`** — Step to Next / Previous conflict hunk
- Automatically saves and stages the file once all hunks are resolved!

---

### 8. 🧠 AI Mentor Chat (`a`)
Conversational Git assistant with real-time repository awareness.
- Ask questions in plain English (e.g. *"How do I split my last commit into two?"*)
- Answers are formatted using Textual's rich **Markdown** renderer.
- Maintains `conversation_id` across turns.
- **`c`** — Clear chat history and reset conversation context

---

### 9. 🧪 AI Test Coverage (`v`)
Available on both Dashboard and Staging screens for any highlighted file:
- Sends file source to the AI coverage endpoint.
- Displays generated test suite in a read-only code viewer (`CoverageModal`).
- **`s`** — Save generated tests to a user-specified file path (prompts via `InputDialog`).

---

## 🏗 Architecture & Code Rules

1. **Separation of Concerns:**
   - Textual screens never import `git` or `httpx` directly.
   - All Git operations are encapsulated inside `megamind/services/git_service.py`.
   - All REST/AI communications are encapsulated inside `megamind/services/api_client.py`.
2. **Non-Blocking UI:**
   - All API network calls and AI generations run in Textual worker threads (`@work(thread=True)`).
   - Semi-transparent `LoadingOverlay` provides user feedback during operations.
3. **Safety & Destructive Operation Guards:**
   - Every destructive operation (hard resets, branch deletion, discarding modifications, reflog restoration) prompts through reusable `ConfirmDialog` stating explicitly what data will be lost.
4. **Resilient Error Handling:**
   - Git and HTTP errors are trapped and displayed in dismissible `ErrorModal` dialogues. The application never terminates with unhandled tracebacks.

---

## 🧪 Testing & Code Quality

Run tests using pytest:

```powershell
Set-Location client
.venv\Scripts\python.exe -m pytest -v
```

Run Ruff linter and formatting checks:

```powershell
Set-Location client
.venv\Scripts\ruff.exe check megamind tests
.venv\Scripts\ruff.exe format --check megamind tests
```

