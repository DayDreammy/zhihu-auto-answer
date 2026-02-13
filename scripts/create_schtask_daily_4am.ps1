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

# Allow running on battery (default Task Scheduler settings may queue forever on laptops).
try {
  $task = Get-ScheduledTask -TaskName $TaskName
  $settings = $task.Settings
  $settings.DisallowStartIfOnBatteries = $false
  $settings.StopIfGoingOnBatteries = $false
  Set-ScheduledTask -TaskName $TaskName -Settings $settings | Out-Null
} catch {
  Write-Warning "Unable to update battery settings for task $TaskName: $($_.Exception.Message)"
}

schtasks.exe /Query /TN $TaskName /V /FO LIST | Out-Host
