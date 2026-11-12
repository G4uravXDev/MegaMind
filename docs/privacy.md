# MEGAMIND Privacy & Security Architecture

MEGAMIND is engineered with **privacy by design**. As a developer tool interacting with proprietary source code, our strict guiding principle is that **your code belongs to you**.

---

## 🛡️ Summary of Privacy Guarantees

| Data Category | Sent to Server? | Stored in Database? | Logged in CloudWatch? |
|---|---|---|---|
| **Whole Repository Files** | ❌ **Never** | ❌ **Never** | ❌ **Never** |
| **Git Credentials / SSH Keys** | ❌ **Never** | ❌ **Never** | ❌ **Never** |
| **Commit Staged Diffs** | ✅ Only on `g` | ❌ **Never** | ❌ **Never** |
| **Conflict Hunks** | ✅ Only on `Shift+G` | ❌ **Never** | ❌ **Never** |
| **Source Code (Coverage)** | ✅ Only on `v` | ❌ **Never** | ❌ **Never** |
| **Mentor Chat Questions** | ✅ Only on `Enter` | ⚠️ Session-only | ❌ **Never** |
| **Audit Metadata (Latency, Action, Status)** | ✅ Yes | ✅ Yes (`AIRequest`) | ✅ Yes |

---

## 🔍 Detailed Data Flows

### 1. What Leaves Your Local Machine?
Data only leaves your machine when you **explicitly initiate an AI action**:
- **Commit Message Generation (`g`)**: Only the staged diff (truncated to 20,000 characters) and the subject lines of the last 10 commits are sent. Unstaged or untracked files are never sent.
- **Merge Conflict Resolution (`Shift+G`)**: Only the current conflict hunk (Ours, Theirs, Base) and 20 lines of surrounding context from the active conflicted file are sent.
- **Test Coverage Generation (`v`)**: Only the single highlighted source file is sent.
- **Mentor Chat (`a`)**: Only your typed question and a lightweight repo status snapshot (branch name, staged count, conflict flag, recent 5 commit subjects) are sent.

### 2. What Is Stored in the Backend Database?
The backend maintains minimal audit and session records:
- **User Account & Token**: Username and hashed credentials for DRF authentication.
- **Audit Logs (`AIRequest`)**: Timestamp, requesting user ID, action name (`commit_message`, `resolve_conflict`, etc.), latency in milliseconds, and HTTP response status.
- **Mentor Conversation Sessions**: If conversation persistence is enabled, chat session IDs and conversational dialogue turns are stored to support multi-turn context.

### 3. What Is NEVER Stored?
- **Diff Content**: Neither staged diffs nor patch hunks are ever persisted to disk, relational databases, or object storage (S3).
- **Source Code**: Source code sent for test coverage analysis is processed entirely in volatile memory during model invocation and discarded immediately.
- **Conflict Hunks**: Divergent branch hunks are never saved to backend databases.

---

## 🪵 CloudWatch & Server Logging Rules

The AWS Lambda function (`megamind-ai`) enforces an absolute zero-payload logging standard in `lambda/handler.py`:

```python
# Permitted log format (Metadata Only)
logger.info("action=%s status=success latency_ms=%d", action, latency_ms)
logger.warning("action=%s status=error code=%s latency_ms=%d", action, err.code, latency_ms)
```

1. **Forbidden in Logs**:
   - Diffs or patch text
   - Source code lines
   - Conflict hunk text
   - User questions or prompt text
   - AWS IAM ARNs or internal exception tracebacks
2. **Recorded in Logs**:
   - Action name (`commit_message`, `resolve_conflict`, `mentor`, `coverage`)
   - Processing latency in milliseconds
   - Result status (`success` or `error`)
   - Stable error codes (`THROTTLED`, `ACCESS_DENIED`, `VALIDATION_ERROR`, etc.)

---

## 🤖 Foundation Model & Bedrock Data Handling

When invoking Amazon Bedrock:
- Requests are processed through AWS private infrastructure.
- In accordance with AWS Bedrock privacy terms, **your prompts and model completions are not used to train or fine-tune AWS or third-party base foundation models**.
- Customer data is processed in accordance with your organization's AWS Data Processing Agreement (DPA).

---

## ⏱️ Data Retention & Deletion

- **Volatile Execution Data**: Diffs and source code exist in Lambda RAM only for the duration of the invocation (typically 1–3 seconds) and are garbage collected immediately upon response completion.
- **Audit Metadata**: Retention policies on the backend database are configurable by the administrator (recommended: 30–90 days for operational auditing).

