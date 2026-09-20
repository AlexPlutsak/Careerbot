$ErrorActionPreference = "SilentlyContinue"

$Root = Split-Path -Parent $PSScriptRoot
$PidFile = Join-Path $Root "data\career_bot.pid"

if (Test-Path $PidFile) {
  $pidText = Get-Content $PidFile -Raw
  $careerBotPid = [int]$pidText.Trim()
  Stop-Process -Id $careerBotPid -Force
  Remove-Item -Path $PidFile -Force
  Write-Host "Career Bot stopped."
  exit
}

Write-Host "Career Bot PID file not found. If the app is open, close the window or stop the Python process manually."
