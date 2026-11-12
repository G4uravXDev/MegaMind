#!/usr/bin/env bash
# Build script to package MegaMind AI Lambda into a deployable zip artifact.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIST_DIR="${SCRIPT_DIR}/dist"
ZIP_PATH="${DIST_DIR}/megamind-ai.zip"
STAGE_DIR="${DIST_DIR}/staging"

echo "Packaging MegaMind AI Lambda function..."

mkdir -p "${DIST_DIR}"
rm -f "${ZIP_PATH}"
rm -rf "${STAGE_DIR}"
mkdir -p "${STAGE_DIR}"

trap 'rm -rf "${STAGE_DIR}"' EXIT

cp "${SCRIPT_DIR}/handler.py" "${STAGE_DIR}/"
cp "${SCRIPT_DIR}/bedrock_client.py" "${STAGE_DIR}/"
cp -r "${SCRIPT_DIR}/prompts" "${STAGE_DIR}/"

# Remove any compiled bytecode
find "${STAGE_DIR}" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "${STAGE_DIR}" -type f -name "*.pyc" -delete 2>/dev/null || true

(cd "${STAGE_DIR}" && zip -r "${ZIP_PATH}" .)

echo "Successfully built deployment package at: ${ZIP_PATH}"

