# MegaMind AI Lambda Service

This AWS Lambda function powers all generative AI workflows for the **MEGAMIND** Git assistant:
- **`commit_message`**: Conventional commit message generation from staged git diffs and commit history.
- **`resolve_conflict`**: Contextual, AST-safe 3-way merge conflict resolution.
- **`mentor`**: Interactive conversational Git advice with live repository context.
- **`coverage`**: Automated unit test generation inferred by file extension and target framework.

The function is built on the **Python 3.12** runtime using **Amazon Bedrock's Converse API** via `boto3`. It carries no third-party dependencies, bundling only native standard library code.

---

## 🛠 Recommended Lambda Configuration

| Setting | Value |
|---|---|
| **Runtime** | Python 3.12 |
| **Architecture** | `arm64` (Graviton2, cost-effective) or `x86_64` |
| **Handler** | `handler.lambda_handler` |
| **Memory** | 256 MB |
| **Timeout** | 30 seconds |
| **Ephemeral Storage** | 512 MB |

### Environment Variables

| Variable | Description | Example Value |
|---|---|---|
| `BEDROCK_MODEL_ID` | Model identifier or cross-region inference profile ID in Amazon Bedrock | `anthropic.claude-3-5-sonnet-20241022-v2:0` or `us.anthropic.claude-3-5-sonnet-20241022-v2:0` |

*Note: The AWS Region is inherited directly from the Lambda runtime environment (`AWS_REGION`). Do not set a custom region variable unless invoking a remote cross-region endpoint.*

---

## 🔐 IAM Execution Role Policy

The Lambda execution role must be granted permissions to invoke models on Amazon Bedrock.

> **Important on Cross-Region Inference Profiles:** If using a cross-region inference profile ID (e.g., IDs starting with `us.` or `eu.`), the IAM policy must grant `bedrock:InvokeModel` on **both** the inference profile ARN and the underlying foundation model ARNs in the supported regions.

### IAM Policy JSON (`megamind-lambda-bedrock-policy.json`)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockInvokeModelPermission",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/*",
        "arn:aws:bedrock:*:*:inference-profile/*"
      ]
    },
    {
      "Sid": "CloudWatchLogsPermission",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

---

## 📦 Packaging and Deployment

### 1. Build the Artifact

From the `lambda/` directory, run the packaging script:

**PowerShell (Windows):**
```powershell
.\build.ps1
```

**Bash (Linux / macOS):**
```bash
chmod +x build.sh
./build.sh
```

This creates the deployment package at `lambda/dist/megamind-ai.zip`.

---

### 2. Deploy via AWS CLI

#### A. Initial Creation:
```powershell
aws lambda create-function `
    --function-name megamind-ai `
    --runtime python3.12 `
    --role arn:aws:iam::<YOUR_ACCOUNT_ID>:role/<YOUR_LAMBDA_ROLE> `
    --handler handler.lambda_handler `
    --zip-file fileb://dist/megamind-ai.zip `
    --timeout 30 `
    --memory-size 256 `
    --environment "Variables={BEDROCK_MODEL_ID=us.anthropic.claude-3-5-sonnet-20241022-v2:0}"
```

#### B. Update Code:
```powershell
aws lambda update-function-code `
    --function-name megamind-ai `
    --zip-file fileb://dist/megamind-ai.zip
```

---

### 3. Deploy via AWS Management Console

1. Navigate to **AWS Lambda** &rarr; **Create function**.
2. Select **Author from scratch**, set Function name to `megamind-ai`, and choose **Python 3.12**.
3. Under **Code source**, click **Upload from** &rarr; **.zip file** and select `lambda/dist/megamind-ai.zip`.
4. In **Runtime settings**, verify that the handler is set to `handler.lambda_handler`.
5. Under **Configuration** &rarr; **General configuration**, set **Timeout** to `30 sec` and **Memory** to `256 MB`.
6. Under **Configuration** &rarr; **Environment variables**, add `BEDROCK_MODEL_ID`.

---

## 🧪 Sample Test Events

Test the function directly in the AWS Console or using `aws lambda invoke`:

### 1. `commit_message`
```json
{
  "action": "commit_message",
  "payload": {
    "diff": "diff --git a/auth.py b/auth.py\n+def login(username, password):\n+    return authenticate(username, password)",
    "recent_commits": [
      "feat(api): add initial endpoints",
      "chore: setup dependencies"
    ],
    "truncated": false
  }
}
```

### 2. `resolve_conflict`
```json
{
  "action": "resolve_conflict",
  "payload": {
    "file_path": "calculator.py",
    "ours": "def add(a: int, b: int) -> int:\n    return a + b",
    "theirs": "def add(a: float, b: float) -> float:\n    \"\"\"Add two numbers.\"\"\"\n    return a + b",
    "base": "def add(a, b):\n    return a + b",
    "context_before": "# Math utilities\n",
    "context_after": "\ndef subtract(a, b):\n    return a - b"
  }
}
```

### 3. `mentor`
```json
{
  "action": "mentor",
  "payload": {
    "question": "How do I amend my last commit message without changing any files?",
    "repo_context": {
      "branch": "feature/login",
      "staged_count": 0,
      "unstaged_count": 0,
      "conflicts": false,
      "recent_commits": ["feat: add login screen"]
    },
    "conversation_id": "test-session-123"
  }
}
```

### 4. `coverage`
```json
{
  "action": "coverage",
  "payload": {
    "file_path": "megamind/utils.py",
    "source": "def slugify(text: str) -> str:\n    return text.strip().lower().replace(' ', '-')"
  }
}
```

---

## 🔒 Security & Privacy Guarantees

1. **Zero Payload Logging**: Diffs, source code, questions, and conflict hunks are **never** logged to Amazon CloudWatch. Only `action`, `status`, `latency_ms`, and stable `error_code` strings are logged.
2. **Prompt Injection Guard**: All user inputs are treated as untrusted and encapsulated inside clear XML-style delimiters (`<UNTRUSTED_DIFF>`, `<UNTRUSTED_SOURCE>`, etc.).
3. **Deterministic Error Handling**: Unhandled exceptions never leak AWS internal traces, stack traces, or credentials to the caller.

