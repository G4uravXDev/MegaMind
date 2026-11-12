# MEGAMIND – AI-Powered Terminal Git Assistant

[![Python Version](https://img.shields.io/badge/python-3.11%2B%20%7C%203.12-blue.svg)](https://www.python.org/)
[![TUI Framework](https://img.shields.io/badge/TUI-Textual-green.svg)](https://textual.textualize.io/)
[![Backend](https://img.shields.io/badge/backend-Django%20REST-red.svg)](https://www.django-rest-framework.org/)
[![AI Engine](https://img.shields.io/badge/AI-Amazon%20Bedrock-orange.svg)](https://aws.amazon.com/bedrock/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**MEGAMIND** is a high-performance terminal UI (TUI) and AI-assisted Git companion designed to streamline everyday developer workflows. It brings visual clarity, safety guards, and intelligent automation directly to your terminal—from staging and conventional commits to interactive 3-panel merge conflict resolution, branch management, topology log graphs, time travel, and contextual AI mentoring.

---

## 🏛️ System Architecture

```text
               ┌─────────────────────────────────────────────────────┐
               │                  MegaMind Terminal (TUI)                 │
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
                                             AWS SDK (boto3)
                                                     │
                                                     ▼
                                          ┌─────────────────────┐
                                          │  AWS Lambda Worker  │
                                          │     (megamind-ai)        │
                                          └──────────┬──────────┘
                                                     │
                                             Converse API
                                                     │
                                                     ▼
                                          ┌─────────────────────┐
                                          │    Amazon Bedrock   │
                                          │ (Claude 3.5 Sonnet) │
                                          └─────────────────────┘
```

The repository is structured as a modular monorepo:

- **[`client/`](client/)**: Full-featured Textual TUI client. Encapsulates all Git operations inside `GitService` (pure GitPython) and all AI communications inside `ApiClient` (HTTPX). Includes non-blocking worker threads, destructive action confirmation dialogs, and an offline mock mode.
- **[`backend/`](backend/)**: Django REST Framework backend providing user authentication (DRF Token), session persistence, and API proxy routing.
- **[`lambda/`](lambda/)**: Serverless AI inference worker running on Python 3.12. Invokes Amazon Bedrock's Converse API with prompt-injection defense, zero-payload logging, and robust throttling retry logic.
- **[`docs/`](docs/)**: In-depth architectural specifications, API schemas, privacy documentation, deployment guides, and testing procedures.

---

## ⚡ Key Features & Keybinding Reference

Press **`?`** anywhere in MEGAMIND to open the instant in-app cheatsheet overlay.

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

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.11 or 3.12
- Git installed and accessible on your `PATH`

---

### 2. Running the Terminal Client

#### Option A: Offline / Mock Mode (Zero Setup Required)
MEGAMIND includes an offline mock mode (`MEGAMIND_MOCK=1`) so you can explore the complete TUI and all workflows immediately without configuring backend servers or AWS credentials:

```powershell
# Windows PowerShell
cd client
.venv\Scripts\Activate.ps1
$env:MEGAMIND_MOCK="1"
python -m megamind
```

To run on a specific repository:
```powershell
python -m megamind C:\path\to\your\repo
```

```bash
# macOS / Linux
cd client
source .venv/bin/activate
export MEGAMIND_MOCK="1"
python -m megamind
```

#### Option B: Connected to Django Backend
```powershell
# Windows PowerShell
cd client
.venv\Scripts\Activate.ps1
$env:MEGAMIND_API_URL="http://127.0.0.1:8000"
$env:MEGAMIND_TOKEN="1ab00d6ac0f622ab56b655f9cfd553dcdff28292"
$env:MEGAMIND_MOCK="0"
python -m megamind
```

---

### 3. Running the Django Backend Server

```powershell
# Windows PowerShell
cd backend
.venv\Scripts\Activate.ps1
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

- **Base URL:** `http://127.0.0.1:8000/`
- **Admin Panel:** `http://127.0.0.1:8000/admin/` (Default admin: `admin` / `AdminPass123!`)
- **Default Token:** `1ab00d6ac0f622ab56b655f9cfd553dcdff28292`

---

### 4. Packaging the AI Lambda Function

The AWS Lambda worker requires Python 3.12 and bundles only standard library code:

```powershell
# Windows PowerShell
cd lambda
.\build.ps1
```

```bash
# macOS / Linux
cd lambda
chmod +x build.sh
./build.sh
```

This creates the deployment artifact at `lambda/dist/megamind-ai.zip`.

---

## ⚙️ Environment Variables Reference

| Component | Variable | Description | Default |
|---|---|---|---|
| **Client** | `MEGAMIND_API_URL` | Base URL of the Django backend | `http://127.0.0.1:8000` |
| **Client** | `MEGAMIND_TOKEN` | Django REST Framework authentication token | *(empty)* |
| **Client** | `MEGAMIND_MOCK` | Enable offline mock mode (`1` = mock, `0` = live API) | `0` |
| **Backend** | `DJANGO_SECRET_KEY` | Cryptographic secret for Django | `change-me` |
| **Backend** | `DATABASE_URL` | Database connection string (PostgreSQL/SQLite) | `sqlite3` (dev) |
| **Backend** | `LAMBDA_FUNCTION_NAME`| Name of deployed AWS Lambda function | `megamind-ai` |
| **Backend** | `AWS_REGION` | AWS Region for backend boto3 calls | `us-east-1` |
| **Lambda** | `BEDROCK_MODEL_ID` | Amazon Bedrock model ID or inference profile | `us.anthropic.claude-3-5-sonnet-20241022-v2:0` |

---

## 🧪 Testing & Verification

The project includes automated test suites covering all tiers:

```powershell
# Run Client UI & Git Tests (65 tests)
cd client
.venv\Scripts\python.exe -m pytest -v

# Run Lambda AI & Privacy Tests (32 tests)
cd lambda
..\client\.venv\Scripts\python.exe -m pytest tests -v

# Lint & Format Checking
.venv\Scripts\ruff.exe check megamind tests
.venv\Scripts\ruff.exe format --check megamind tests
```

---

## 📚 In-Depth Documentation

For detailed technical guides, see the [`docs/`](docs/) directory:

- 🏗️ [**Architecture & Design**](docs/architecture.md): Sequence diagrams, request flows, and component responsibilities.
- 📡 [**REST API Reference**](docs/api.md): Endpoint specifications, payload schemas, and PowerShell examples.
- 🔒 [**Privacy & Security**](docs/privacy.md): Zero-payload logging policy, data boundaries, and retention guarantees.
- 🚀 [**Production Deployment**](docs/deployment.md): PostgreSQL provisioning, Gunicorn/Nginx setup, Lambda deployment, and cost estimates.
- 🧪 [**Testing Guide**](docs/testing.md): Pytest workflows, mocked Converse API tests, and mock mode usage.
- ⚡ [**Lambda Service README**](lambda/README.md): IAM policies, cross-region inference profiles, and sample AWS test events.
