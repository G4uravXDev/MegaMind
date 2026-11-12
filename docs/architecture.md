# MEGAMIND Architecture & System Design

This document details the architectural topology, data boundaries, and operational sequence flows of **MEGAMIND**, an AI-powered terminal Git assistant.

---

## 🏛️ High-Level System Topology

```text
┌────────────────────────────────────────────────────────────────────────┐
│                              LOCAL MACHINE                             │
│                                                                        │
│   ┌──────────────────────────┐         ┌───────────────────────────┐   │
│   │   Git Repository (.git)  │         │     MegaMind Client (TUI)      │   │
│   │   Working Tree & Staging │◄───────►│  Textual + Pure GitPython │   │
│   └──────────────────────────┘         └─────────────┬─────────────┘   │
│                                                      │                 │
│                                                      │ HTTPS REST      │
│                                                      │ (Token Auth)    │
└──────────────────────────────────────────────────────┼─────────────────┘
                                                       │
                                                       ▼
┌────────────────────────────────────────────────────────────────────────┐
│                          BACKEND INFRASTRUCTURE                        │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │                      Django REST Backend                       │   │
│   │            (Session Management, Auth, Audit Logger)            │   │
│   └──────────────────────────────┬─────────────────────────────────┘   │
│                                  │                                     │
│                                  │ AWS SDK (boto3)                     │
│                                  │ lambda:InvokeFunction               │
│                                  ▼                                     │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │                       AWS Lambda (megamind-ai)                      │   │
│   │         (Payload Validation, Prompt Safety, Error Guard)        │   │
│   └──────────────────────────────┬─────────────────────────────────┘   │
│                                  │                                     │
│                                  │ Converse API                        │
│                                  │ bedrock:InvokeModel                 │
│                                  ▼                                     │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │                         Amazon Bedrock                         │   │
│   │           (Claude 3.5 Sonnet / Foundation AI Models)           │   │
│   └────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🧩 Architectural Components

### 1. Client (`client/`)
- **UI Framework**: Built on [Textual](https://textual.textualize.io/) providing an asynchronous, full-screen terminal interface with keyboard-centric navigation.
- **Git Service (`GitService`)**: Encapsulates all interactions with the local `.git` repository using pure `GitPython`. Screens and widgets never import `git` directly.
- **API Client (`ApiClient`)**: Pure `httpx` REST client. Handles token authentication, diff truncation (capped at 20,000 characters), and offline fallback mock mode (`MEGAMIND_MOCK=1`).
- **Safety First**: Destructive operations (`git reset --hard`, branch deletion, change discarding, reflog restoration) are strictly intercepted by an interactive modal `ConfirmDialog` detailing the exact data at risk.
- **Non-Blocking UI**: Background worker threads (`@work(thread=True)`) handle all network calls and Git diff computations with loading overlays.

### 2. Backend API (`backend/`)
- **Web Framework**: Built with Django and Django REST Framework (DRF).
- **Authentication**: Token-based authentication (`rest_framework.authtoken`) protecting all AI endpoints.
- **Orchestration**: Receives sanitized client payloads, attaches user context, logs request metadata, and invokes the AWS Lambda AI worker via `boto3`.

### 3. AI Worker Lambda (`lambda/`)
- **Runtime**: Python 3.12 running with zero third-party dependencies.
- **Model Interface**: Connects to Amazon Bedrock via the unified **Converse API** (`bedrock-runtime.converse()`).
- **Prompt Injection Defense**: Explicitly wraps all code, diffs, and user questions within XML-style delimiters (`<UNTRUSTED_DIFF>`, `<UNTRUSTED_SOURCE>`) and instructs the foundation model never to follow instructions found within untrusted content.
- **Deterministic Contract**: Always returns `{"ok": true, "data": {...}}` or `{"ok": false, "error": {"code": "...", "message": "..."}}`. Never raises unhandled exceptions or leaks AWS internal error details.

---

## 🔒 Data Ownership & Boundary Rules

### What Stays on Your Machine
- **Full Source Code**: Your local files and source tree are never uploaded in bulk.
- **Git History & Credentials**: Local SSH keys, personal access tokens, Git config, stash lists, and reflog records remain exclusively on your device.
- **Execution of Git Commands**: All branch switching, committing, resetting, and stashing happen locally via `git`. No remote service has write or execution access to your machine.

### What Leaves the Machine
- **Staged Diffs (for Commit Message Generation)**: Sent only when you explicitly press `g` on the Commit Screen. Diffs are strictly truncated to a maximum of 20,000 characters.
- **Conflict Hunk Content (for Conflict Resolution)**: Sent only when you press `Shift+G` on an active merge conflict hunk. Sends only the immediate conflicting lines plus up to 20 lines of surrounding context.
- **Selected File Source (for Test Coverage)**: Sent only when you press `v` on a highlighted file in the Dashboard or Staging view.
- **Mentor Prompts & Repo Metadata**: Sent only when you type a question and submit it in the Mentor view (`a`). Metadata is limited to branch name, counts of staged/unstaged files, and the last 5 commit subject lines.

---

## 🔄 Sequence Diagrams

### 1. Commit Message Generation Flow

```text
Developer             MegaMind Client (TUI)           Django API Backend             AWS Lambda (megamind-ai)             Amazon Bedrock
    │                        │                            │                              │                             │
    │  Presses 'g' on        │                            │                              │                             │
    │  Commit Screen         │                            │                              │                             │
    │───────────────────────►│                            │                              │                             │
    │                        │ Compute staged diff        │                              │                             │
    │                        │ & truncate to 20k chars    │                              │                             │
    │                        │                            │                              │                             │
    │                        │ POST /api/ai/commit-message│                              │                             │
    │                        │ Authorization: Token xxx   │                              │                             │
    │                        │───────────────────────────►│                              │                             │
    │                        │ (Loading overlay active)   │ Authenticate token           │                             │
    │                        │                            │ Wrap payload                 │                             │
    │                        │                            │                              │                             │
    │                        │                            │ lambda.invoke()              │                             │
    │                        │                            │ action="commit_message"      │                             │
    │                        │                            │─────────────────────────────►│                             │
    │                        │                            │                              │ Build prompt + delimiters   │
    │                        │                            │                              │ bedrock.converse()          │
    │                        │                            │                              │────────────────────────────►│
    │                        │                            │                              │                             │ Analyze diff
    │                        │                            │                              │                             │ Infer style
    │                        │                            │                              │◄────────────────────────────│
    │                        │                            │                              │ Parse & strip code fences   │
    │                        │                            │◄─────────────────────────────│                             │
    │                        │                            │ {"ok": true, "data": {...}}  │                             │
    │                        │◄───────────────────────────│                              │                             │
    │                        │ {"message": "feat: ..."}   │                              │                             │
    │                        │                            │                              │                             │
    │ Populates commit       │                            │                              │                             │
    │ message text area      │                            │                              │                             │
    │◄───────────────────────│                            │                              │                             │
```

---

### 2. Interactive Merge Conflict Resolution Flow

```text
Developer             MegaMind Client (TUI)           Django API Backend             AWS Lambda (megamind-ai)             Amazon Bedrock
    │                        │                            │                              │                             │
    │  Presses 'Shift+G' on  │                            │                              │                             │
    │  conflicted hunk       │                            │                              │                             │
    │───────────────────────►│                            │                              │                             │
    │                        │ Extract Ours, Theirs, Base │                              │                             │
    │                        │ + 20 lines context         │                              │                             │
    │                        │                            │                              │                             │
    │                        │ POST /api/ai/resolve-conflict                             │                             │
    │                        │───────────────────────────►│                              │                             │
    │                        │                            │ lambda.invoke()              │                             │
    │                        │                            │ action="resolve_conflict"    │                             │
    │                        │                            │─────────────────────────────►│                             │
    │                        │                            │                              │ Build prompt                │
    │                        │                            │                              │ Require strict JSON schema  │
    │                        │                            │                              │ bedrock.converse()          │
    │                        │                            │                              │────────────────────────────►│
    │                        │                            │                              │                             │ Synthesize hunk
    │                        │                            │                              │◄────────────────────────────│
    │                        │                            │                              │ Validate JSON & strip fences│
    │                        │                            │                              │ Remove residual markers     │
    │                        │                            │◄─────────────────────────────│                             │
    │                        │◄───────────────────────────│                              │                             │
    │                        │ {"resolution": "...", ...} │                              │                             │
    │                        │                            │                              │                             │
    │ Displays resolution in │                            │                              │                             │
    │ center editable panel  │                            │                              │                             │
    │◄───────────────────────│                            │                              │                             │
    │                        │                            │                              │                             │
    │ Presses 'm' to apply   │                            │                              │                             │
    │───────────────────────►│ Write clean hunk to file   │                              │                             │
    │                        │ When all hunks resolved:   │                              │                             │
    │                        │ git.add(conflicted_file)   │                              │                             │
```

