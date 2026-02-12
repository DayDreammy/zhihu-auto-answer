param(
  [string]$TaskName = "ZhihuAutoAnswerDaily",
  [string]$RepoDir = (Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent),
  [string]$StartTime = "04:00"
)

$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $RepoDir "scripts\\run_daily_zhihu.ps1"
if (!(Test-Path $scriptPath)) {
  throw "Missing script: $scriptPath"
}

$tr = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""

schtasks.exe /Create /F `
  /TN $TaskName `
  /SC DAILY `
  /ST $StartTime `
  /RL LIMITED `
  /TR $tr | Out-Host

schtasks.exe /Query /TN $TaskName /V /FO LIST | Out-Host

