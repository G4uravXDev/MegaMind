# Build script to package MegaMind AI Lambda into a deployable zip artifact.
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$distDir = Join-Path $scriptDir "dist"
$zipPath = Join-Path $distDir "megamind-ai.zip"

Write-Host "Packaging MegaMind AI Lambda function..." -ForegroundColor Cyan

# Ensure dist directory exists
if (-not (Test-Path $distDir)) {
    New-Item -ItemType Directory -Path $distDir | Out-Null
}

# Remove existing zip if present
if (Test-Path $zipPath) {
    Remove-Item -Force $zipPath
}

# Temporary staging directory to assemble files cleanly
$tempStage = Join-Path $distDir "staging"
if (Test-Path $tempStage) {
    Remove-Item -Recurse -Force $tempStage
}
New-Item -ItemType Directory -Path $tempStage | Out-Null

try {
    # Copy source files
    Copy-Item (Join-Path $scriptDir "handler.py") -Destination $tempStage
    Copy-Item (Join-Path $scriptDir "bedrock_client.py") -Destination $tempStage
    Copy-Item -Recurse (Join-Path $scriptDir "prompts") -Destination $tempStage

    # Clean up __pycache__ in staging if present
    Get-ChildItem -Path $tempStage -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force

    # Create archive
    Compress-Archive -Path "$tempStage\*" -DestinationPath $zipPath -Force
    Write-Host "Successfully built deployment package at: $zipPath" -ForegroundColor Green
}
finally {
    if (Test-Path $tempStage) {
        Remove-Item -Recurse -Force $tempStage
    }
}

