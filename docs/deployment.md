# MEGAMIND Production Deployment Guide

This guide details deploying the **MEGAMIND** full-stack system: provisioning the PostgreSQL database, deploying the Django REST backend with Gunicorn, deploying the AWS Lambda worker, configuring environment variables, and establishing AWS budget monitoring.

---

## 🏗️ Architecture Overview

```text
Developer Terminal ──(HTTPS)──► Nginx Reverse Proxy
                                      │
                                      ▼
                              Gunicorn (WSGI)
                                      │
                              Django REST API ────► PostgreSQL Database
                                      │
                                      ▼ (AWS SDK / boto3)
                              AWS Lambda (megamind-ai)
                                      │
                                      ▼
                              Amazon Bedrock (Claude 3.5)
```

---

## 🗄️ 1. PostgreSQL Database Setup

1. Install and start PostgreSQL (version 15+ recommended):
   ```bash
   sudo apt-get update
   sudo apt-get install -y postgresql postgresql-contrib
   sudo systemctl enable postgresql
   sudo systemctl start postgresql
   ```

2. Create the database and dedicated service user:
   ```bash
   sudo -u postgres psql -c "CREATE USER megamind_user WITH PASSWORD 'SecurePasswordHere123!';"
   sudo -u postgres psql -c "CREATE DATABASE megamind OWNER megamind_user;"
   sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE megamind TO megamind_user;"
   ```

---

## ⚙️ 2. Backend Server Deployment (Linux / Ubuntu)

### 1. Clone & Set Up Virtual Environment
```bash
git clone https://github.com/YourOrg/megamind.git /opt/megamind
cd /opt/megamind/backend

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn
```

### 2. Configure Environment Variables (`backend/.env`)
Create `/opt/megamind/backend/.env` with production settings:

```dotenv
DJANGO_SECRET_KEY=generate-a-strong-random-50-char-secret-key-here
DEBUG=False
ALLOWED_HOSTS=megamind.yourdomain.com,127.0.0.1

DATABASE_URL=postgres://megamind_user:SecurePasswordHere123!@127.0.0.1:5432/megamind

AWS_REGION=us-east-1
LAMBDA_FUNCTION_NAME=megamind-ai
```

### 3. Run Migrations & Collect Static Files
```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput
```

### 4. Create Systemd Service for Gunicorn (`/etc/systemd/system/megamind-backend.service`)
```ini
[Unit]
Description=MEGAMIND Django Backend Daemon
After=network.target postgresql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/megamind/backend
ExecStart=/opt/megamind/backend/.venv/bin/gunicorn \
          --workers 3 \
          --bind 127.0.0.1:8000 \
          config.wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable megamind-backend
sudo systemctl start megamind-backend
```

### 5. Configure Nginx Reverse Proxy (`/etc/nginx/sites-available/megamind`)
```nginx
server {
    listen 80;
    server_name megamind.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /opt/megamind/backend/static/;
    }
}
```

---

## ⚡ 3. Deploying the AI Worker Lambda

### 1. Build the Lambda Package
On your development machine:
```powershell
# Windows
cd lambda
.\build.ps1
```
*(Or on Linux/macOS: `./build.sh`)*

This produces `lambda/dist/megamind-ai.zip`.

### 2. Create the AWS Lambda Function
```powershell
aws lambda create-function `
    --function-name megamind-ai `
    --runtime python3.12 `
    --role arn:aws:iam::<YOUR_ACCOUNT_ID>:role/megamind-lambda-execution-role `
    --handler handler.lambda_handler `
    --zip-file fileb://dist/megamind-ai.zip `
    --timeout 30 `
    --memory-size 256 `
    --environment "Variables={BEDROCK_MODEL_ID=us.anthropic.claude-3-5-sonnet-20241022-v2:0}"
```

### 3. Attach IAM Policy
Ensure the role has permission to invoke Bedrock models (see policy in [`lambda/README.md`](file:///c:/Users/gaura/OneDrive/Desktop/Pre/lambda/README.md)).

---

## 🔌 4. Connecting the Client (Switching Off Mock Mode)

To take developers off offline mock mode and connect them to production:

```powershell
# Windows PowerShell
$env:MEGAMIND_API_URL="https://megamind.yourdomain.com"
$env:MEGAMIND_TOKEN="<user-drf-token>"
$env:MEGAMIND_MOCK="0"
python -m megamind
```

```bash
# Linux / macOS
export MEGAMIND_API_URL="https://megamind.yourdomain.com"
export MEGAMIND_TOKEN="<user-drf-token>"
export MEGAMIND_MOCK="0"
python -m megamind
```

---

## 💰 5. Cost Estimation & AWS Budget Alerts

### Estimated Usage Costs

| Service | Component | Estimated Unit Cost | Typical Cost per 1,000 Invocations |
|---|---|---|---|
| **AWS Lambda** | 256 MB RAM, ~1.5s execution | $0.0000000021 / ms | **~$0.03** |
| **Amazon Bedrock** (Claude 3.5 Sonnet) | Input Tokens: ~$3.00 / 1M<br>Output Tokens: ~$15.00 / 1M | ~500 input + 100 output tokens / commit | **~$3.00** |
| **AWS CloudWatch** | Ingestion & Metric retention | $0.50 / GB | **<$0.05** |

*Total estimated cost for 1,000 AI operations is roughly **$3.08**.*

### Setting Up an AWS Billing Alert
1. In the **AWS Billing & Cost Management** Console, navigate to **Budgets**.
2. Click **Create budget** &rarr; Select **Cost budget (recommended)**.
3. Name the budget `megamind-ai-monthly-budget` and set a monthly threshold (e.g. `$25.00`).
4. Configure an email notification alert when actual or forecasted charges exceed **80%** of your budget.

