# KnowFlow AI — 全 Docker 一键部署 + 上线前检查 + 验收
# 用法:
#   .\deploy_all.ps1
#   .\deploy_all.ps1 -Production    # 额外启动 nginx (profile production)
#   .\deploy_all.ps1 -SkipTests     # 仅构建与启动

param(
    [switch]$Production,
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$Root = if ($PSScriptRoot) { $PSScriptRoot } else { Get-Location }
Set-Location $Root

Write-Host "==> Project root: $Root"

if (-not (Test-Path ".env")) {
    Write-Host "WARN: .env not found. Copy from .env.example first:" -ForegroundColor Yellow
    Write-Host "  copy .env.example .env"
    exit 1
}

function Test-EnvLine([string]$Name) {
    $line = Get-Content ".env" -ErrorAction SilentlyContinue | Where-Object { $_ -match "^\s*$Name\s*=" } | Select-Object -First 1
    if (-not $line) { return $null }
    return ($line -split "=", 2)[1].Trim().Trim('"').Trim("'")
}

Write-Host "`n==> Pre-flight checks..."
$secret = Test-EnvLine "SECRET_KEY"
if (-not $secret -or $secret -match "change-me|replace-with") {
    Write-Host "  [WARN] SECRET_KEY not set for production — set a random 32+ char value in .env" -ForegroundColor Yellow
}

$promoteOn = Test-EnvLine "PROMOTE_USER_ON_START"
if ($promoteOn -eq "false") {
    Write-Host "  [WARN] PROMOTE_USER_ON_START=false — MJZ owner admin will not be re-applied on restart" -ForegroundColor Yellow
} else {
    $pe = Test-EnvLine "PROMOTE_USER_EMAIL"
    $pu = Test-EnvLine "PROMOTE_USER_USERNAME"
    Write-Host "  [OK] Permanent admin promote: email=$pe username=$pu"
}

$llmKey = Test-EnvLine "LLM_API_KEY"
if (-not $llmKey -or $llmKey -match "your_.*_here") {
    Write-Host "  [WARN] LLM_API_KEY missing or placeholder — chat will fail until configured" -ForegroundColor Yellow
}

Write-Host "`n==> Building Docker images (backend, celery-worker, frontend)..."
docker compose build backend celery-worker frontend
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$upArgs = @("up", "-d", "postgres", "redis", "chromadb", "backend", "celery-worker", "frontend")
if ($Production) {
    $upArgs += "--profile", "production"
    $upArgs += "nginx"
}
Write-Host "`n==> Starting containers: $($upArgs -join ' ')..."
docker compose @upArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n==> Container status:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

Write-Host "`n==> Waiting 20s for backend health..."
Start-Sleep -Seconds 20

Write-Host "`n==> Backend health check:"
try {
    $raw = curl.exe -sf http://localhost:8000/api/health
    if (-not $raw) { throw "Empty response" }
    $health = $raw | ConvertFrom-Json
    Write-Host "  status=$($health.status) service=$($health.service) env=$($health.env)"
    if ($health.status -ne "ok") { throw "status is not ok" }
} catch {
    Write-Host "FAIL: backend health check failed. Logs:" -ForegroundColor Red
    docker compose logs backend --tail 50
    exit 1
}

Write-Host "`n==> MJZ admin promote (from backend logs)..."
docker compose logs backend 2>&1 | Select-String -Pattern "Promoted user|already role=admin|Created admin" | Select-Object -Last 5

if ($Production) {
    $nginxPort = Test-EnvLine "NGINX_PORT"
    if (-not $nginxPort) { $nginxPort = "80" }
    Write-Host "`n  Nginx entry: http://localhost:$nginxPort"
}

if ($SkipTests) {
    Write-Host "`n==> Done (tests skipped)."
    exit 0
}

Write-Host "`n==> Backend e2e acceptance (host -> localhost:8000)..."
Push-Location backend
python scripts/e2e_acceptance.py
$e2eExit = $LASTEXITCODE
Pop-Location
if ($e2eExit -ne 0) { exit $e2eExit }

Write-Host "`n==> Backend pytest (in container)..."
docker compose exec -T backend pytest tests/ -q --tb=no
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n==> All checks passed."
Write-Host "  Frontend:  http://localhost:3000"
Write-Host "  API:       http://localhost:8000"
Write-Host "  API docs:  http://localhost:8000/docs"
Write-Host "  Metrics:   http://localhost:8000/api/metrics"
Write-Host "  Checklist: docs/zh/17-上线前检查清单.md"
