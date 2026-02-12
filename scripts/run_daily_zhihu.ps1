param(
  [string]$RepoDir = (Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent),
  [int]$MaxQuestions = 10,
  [int]$Concurrency = 2,
  [int]$FlushDraftsEvery = 5
)

$ErrorActionPreference = "Stop"

Set-Location $RepoDir

# Ensure Python sees env vars even if they were set via `setx` earlier.
$hook = [Environment]::GetEnvironmentVariable("FEISHU_WEBHOOK_URL", "User")
if ($hook) { $env:FEISHU_WEBHOOK_URL = $hook }

$token = [Environment]::GetEnvironmentVariable("CABINET_API_TOKEN", "User")
if ($token) { $env:CABINET_API_TOKEN = $token }

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

New-Item -ItemType Directory -Force -Path (Join-Path $RepoDir "logs") | Out-Null

$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$outLog = Join-Path $RepoDir "logs\\scheduled_$ts.log"

$args = @(
  "main.py",
  "--headless",
  "--no-persistent-profile",
  "--answer-type", "deep_research",
  "--max-questions", "$MaxQuestions",
  "--flush-drafts-every", "$FlushDraftsEvery"
)

"[$(Get-Date -Format o)] starting: python $($args -join ' ')" | Out-File -FilePath $outLog -Encoding utf8

& python @args *>> $outLog
exit $LASTEXITCODE

