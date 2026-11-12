# MEGAMIND Testing & Verification Guide

This guide describes how to run automated test suites and linters across all layers of the MEGAMIND project: the Textual terminal client (`client/`), the Django backend (`backend/`), and the AI Lambda service (`lambda/`).

---

## 🧪 Quick Test Matrix

| Component | Test Framework | Command | Test Count |
|---|---|---|---|
| **Client (TUI)** | Pytest + AnyIO + Textual `run_test` | `cd client; .venv\Scripts\python.exe -m pytest -v` | **65 tests** |
| **Lambda (AI Service)** | Pytest + `unittest.mock` | `cd lambda; ..\client\.venv\Scripts\python.exe -m pytest tests -v` | **32 tests** |
| **Backend (Django)** | Django TestCase / Pytest | `cd backend; .venv\Scripts\python.exe manage.py test` | Backend suite |
| **Code Formatting** | Ruff | `ruff check; ruff format --check` | 100% clean |

---

## 💻 1. Running Client Tests

The client test suite validates Textual async screen rendering, modal workflows, keybindings, and pure Git operations:

```powershell
# Windows PowerShell
cd client
.venv\Scripts\Activate.ps1
python -m pytest -v
```

```bash
# macOS / Linux
cd client
source .venv/bin/activate
pytest -v
```

### What Is Covered in Client Tests
- **Navigation & Screens**: Switching between Dashboard, Staging, Commit, Branches, Log Graph, Time Travel, Conflicts, and Mentor.
- **Safety Dialogs**: Testing `ConfirmDialog` cancellation and confirmation for hard resets, stash drops, and branch deletions.
- **Conflict Parser**: Verifying 2-way and 3-way conflict parsing, hunk stepping, and replacement synthesis.
- **Diff View & Truncation**: Syntax coloring and 20,000-character payload truncation.

---

## ⚡ 2. Running Lambda Tests

The Lambda test suite tests prompt construction, JSON parsing, code fence removal, Bedrock throttling retries, error code mappings, and zero-payload logging guarantees:

```powershell
# Windows PowerShell
cd lambda
..\client\.venv\Scripts\python.exe -m pytest tests -v
```

```bash
# macOS / Linux
cd lambda
pytest tests -v
```

### What Is Covered in Lambda Tests
- **Action Routing**: Validating `commit_message`, `resolve_conflict`, `mentor`, `coverage`, and returning `UNKNOWN_ACTION` for invalid requests.
- **Payload Validation**: Verifying required keys (`diff`, `file_path`, `ours`, `theirs`, `question`, `source`).
- **Prompt Injection Defense**: Confirming all inputs are safely enclosed within untrusted delimiters.
- **Converse API Mocking**: Simulating Bedrock throttling (`ThrottlingException`), retry with backoff, and access denied errors (`AccessDeniedException`).
- **Privacy Assertion**: Capturing log streams and verifying that secret tokens, diffs, code, and questions **never** appear in stdout/logs.

---

## 🛡️ 3. Using Offline Mock Mode

Developers can run and test the complete MEGAMIND terminal interface locally without requiring an active backend or AWS credentials by setting `MEGAMIND_MOCK=1`:

```powershell
# Windows PowerShell
cd client
$env:MEGAMIND_MOCK="1"
.venv\Scripts\python.exe -m megamind
```

```bash
# macOS / Linux
cd client
export MEGAMIND_MOCK="1"
python -m megamind
```

In mock mode:
- Commit messages are generated from local diff summaries.
- Merge conflicts synthesize a merged representation with mock tags.
- The AI Mentor answers Git questions with real-time branch status.
- Test coverage generates a sample test suite for the target file.

---

## 🧹 4. Running Linting & Formatting Checks

All Python code adheres to PEP 8, strict type hints, and passes [Ruff](https://astral.sh/ruff) without errors:

```powershell
# Check client
cd client
.venv\Scripts\ruff.exe check megamind tests
.venv\Scripts\ruff.exe format --check megamind tests

# Check lambda
cd lambda
..\client\.venv\Scripts\ruff.exe check . tests
..\client\.venv\Scripts\ruff.exe format --check . tests
```

