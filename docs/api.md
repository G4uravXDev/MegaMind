# MegaMind REST API Reference

This document provides the complete API specification for the **MEGAMIND** backend endpoints consumed by the terminal client.

---

## 🔑 Authentication

All endpoints require standard Django REST Framework Token Authentication passed in the `Authorization` header:

```http
Authorization: Token <your_token_here>
Content-Type: application/json
```

Requests lacking a valid token return `401 Unauthorized`:
```json
{
  "detail": "Invalid token."
}
```

---

## 🚦 Common Error Format & Status Codes

When an error occurs, the API returns a structured JSON payload:

```json
{
  "error": {
    "code": "INVALID_PAYLOAD",
    "message": "Missing required field 'diff'."
  }
}
```

### Standard Status Codes
- `200 OK`: Request succeeded.
- `400 Bad Request`: Payload validation failed or required keys were omitted.
- `401 Unauthorized`: Missing or invalid authentication token.
- `429 Too Many Requests`: Request throttled by backend rate limits or upstream AI model.
- `502 Bad Gateway / 500 Internal Server Error`: AI Lambda or Bedrock model invocation failed.

---

## 📡 Endpoints

---

### 1. Generate Commit Message

Generates a concise Conventional Commit message based on staged diff analysis and recent commit style.

- **Method**: `POST`
- **Path**: `/api/ai/commit-message/`
- **Limits**: Staged `diff` string is capped at **20,000 characters** (client automatically truncates before sending).

#### Request Payload
```json
{
  "diff": "diff --git a/app.py b/app.py\n+def hello():\n+    return 'world'",
  "recent_commits": [
    "feat(core): initial setup",
    "chore: configure dependencies"
  ],
  "truncated": false
}
```

#### Response Payload (`200 OK`)
```json
{
  "message": "feat(core): add greeting function"
}
```

#### PowerShell Example
```powershell
$headers = @{
    "Authorization" = "Token 1ab00d6ac0f622ab56b655f9cfd553dcdff28292"
    "Content-Type"  = "application/json"
}
$body = @{
    diff = "diff --git a/auth.py b/auth.py`n+def check_token(t): return bool(t)"
    recent_commits = @("feat: add login screen", "docs: update readme")
    truncated = $false
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/ai/commit-message/" `
    -Method Post `
    -Headers $headers `
    -Body $body
```

---

### 2. Resolve Merge Conflict

Synthesizes a clean replacement for a conflicted hunk using surrounding context and 3-way parent comparisons.

- **Method**: `POST`
- **Path**: `/api/ai/resolve-conflict/`
- **Limits**: Surrounding context is typically limited to 20 lines before and after the hunk.

#### Request Payload
```json
{
  "file_path": "services/calculator.py",
  "ours": "def compute(x: int) -> int:\n    return x * 2",
  "theirs": "def compute(x: float) -> float:\n    \"\"\"Doubles input.\"\"\"\n    return x * 2.0",
  "base": "def compute(x):\n    return x * 2",
  "context_before": "# Math calculation service\n",
  "context_after": "\ndef reset(): pass"
}
```

#### Response Payload (`200 OK`)
```json
{
  "resolution": "def compute(x: int | float) -> int | float:\n    \"\"\"Doubles input.\"\"\"\n    return x * 2",
  "explanation": "Merged type annotations into union and preserved docstring from incoming branch."
}
```

#### PowerShell Example
```powershell
$headers = @{
    "Authorization" = "Token 1ab00d6ac0f622ab56b655f9cfd553dcdff28292"
    "Content-Type"  = "application/json"
}
$body = @{
    file_path = "config.py"
    ours = "TIMEOUT = 30"
    theirs = "TIMEOUT = 60"
    base = "TIMEOUT = 10"
    context_before = "# Global configuration`n"
    context_after = "`nDEBUG = True"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/ai/resolve-conflict/" `
    -Method Post `
    -Headers $headers `
    -Body $body
```

---

### 3. AI Git Mentor Chat

Conversational Git advice tailored to the user's live repository context.

- **Method**: `POST`
- **Path**: `/api/ai/mentor/`
- **Limits**: Conversation history includes up to the last 10 messages for context preservation.

#### Request Payload
```json
{
  "question": "How do I unstage a file without losing my edits?",
  "repo_context": {
    "branch": "main",
    "staged_count": 1,
    "unstaged_count": 0,
    "conflicts": false,
    "recent_commits": ["chore: initial commit"]
  },
  "conversation_id": "session-user-123",
  "history": [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hello! I am your MEGAMIND Git mentor. How can I help?"}
  ]
}
```

#### Response Payload (`200 OK`)
```json
{
  "answer": "To unstage your file while keeping your modifications intact in your working tree, run:\n\n```bash\ngit restore --staged <file>\n```\n\n*(Or in older Git versions: `git reset HEAD <file>`)*",
  "conversation_id": "session-user-123"
}
```

#### PowerShell Example
```powershell
$headers = @{
    "Authorization" = "Token 1ab00d6ac0f622ab56b655f9cfd553dcdff28292"
    "Content-Type"  = "application/json"
}
$body = @{
    question = "What is the difference between git fetch and git pull?"
    repo_context = @{
        branch = "main"
        staged_count = 0
        unstaged_count = 0
    }
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/ai/mentor/" `
    -Method Post `
    -Headers $headers `
    -Body $body
```

---

### 4. Generate Test Coverage

Generates automated unit tests for a target source file, automatically inferring language and framework.

- **Method**: `POST`
- **Path**: `/api/ai/coverage/`

#### Request Payload
```json
{
  "file_path": "megamind/utils.py",
  "source": "def is_clean_string(val: str) -> bool:\n    return bool(val and val.strip())"
}
```

#### Response Payload (`200 OK`)
```json
{
  "tests": "import pytest\nfrom megamind.utils import is_clean_string\n\ndef test_is_clean_string_valid():\n    assert is_clean_string('hello') is True\n\ndef test_is_clean_string_empty():\n    assert is_clean_string('') is False\n    assert is_clean_string('   ') is False"
}
```

#### PowerShell Example
```powershell
$headers = @{
    "Authorization" = "Token 1ab00d6ac0f622ab56b655f9cfd553dcdff28292"
    "Content-Type"  = "application/json"
}
$body = @{
    file_path = "math_ops.py"
    source = "def add(a, b): return a + b"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/ai/coverage/" `
    -Method Post `
    -Headers $headers `
    -Body $body
```

