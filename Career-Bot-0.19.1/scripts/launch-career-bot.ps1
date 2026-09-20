$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Url = "http://127.0.0.1:8765/"
$ExpectedVersion = "0.21.7"
$PidFile = Join-Path $Root "data\career_bot.pid"
$ErrorLog = Join-Path $Root "data\launcher-error.log"
$BundledPython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$Python = if (Test-Path $BundledPython) { $BundledPython } else { "python" }

function Test-CareerBot {
  try {
    $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
    return $response.StatusCode -eq 200
  } catch {
    return $false
  }
}

function Get-CareerBotVersion {
  try {
    $health = Invoke-RestMethod -Uri ($Url + "api/health") -TimeoutSec 2
    if ($health.ok -eq $true) { return [string]$health.version }
  } catch {
    return $null
  }
  return $null
}

function Start-CareerBotServer {
  $serverPath = Join-Path $Root "career_bot\server.py"
  $process = Start-Process -FilePath $Python -ArgumentList "`"$serverPath`"" -WorkingDirectory $Root -WindowStyle Hidden -PassThru
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $PidFile) | Out-Null
  Set-Content -Path $PidFile -Value $process.Id -Encoding ascii

  for ($i = 0; $i -lt 20; $i++) {
    if (Test-CareerBot) { return }
    Start-Sleep -Milliseconds 400
  }

  throw "Career Bot server did not start on $Url"
}

function Get-CareerBotListenerPids {
  $lines = netstat -ano -p tcp 2>$null
  return @($lines | ForEach-Object {
    if ($_ -match '^\s*TCP\s+127\.0\.0\.1:8765\s+\S+\s+LISTENING\s+(\d+)\s*$') {
      [int]$Matches[1]
    }
  } | Where-Object { $_ -gt 0 } | Select-Object -Unique)
}

function Stop-PreviousCareerBot {
  $listenerPids = Get-CareerBotListenerPids
  if (-not $listenerPids -and (Test-Path $PidFile)) {
    $rawPid = (Get-Content $PidFile -Raw).Trim()
    $parsedPid = 0
    if ([int]::TryParse($rawPid, [ref]$parsedPid)) { $listenerPids = @($parsedPid) }
  }
  foreach ($careerBotPid in $listenerPids) {
    $process = Get-Process -Id $careerBotPid -ErrorAction SilentlyContinue
    if ($process -and $process.ProcessName -like 'python*') {
      Stop-Process -Id $careerBotPid -Force -ErrorAction Stop
      try { Wait-Process -Id $careerBotPid -Timeout 8 -ErrorAction SilentlyContinue } catch { }
    }
  }
  Remove-Item -Path $PidFile -Force -ErrorAction SilentlyContinue

  for ($i = 0; $i -lt 20; $i++) {
    if (-not (Test-CareerBot)) { return }
    if ((Get-CareerBotVersion) -eq $ExpectedVersion) { return }
    Start-Sleep -Milliseconds 300
  }
  throw "The previous version was stopped, but port 8765 is still busy. Restart Windows or free the port and try again."
}

function Open-AppWindow {
  $edge = @(
    Join-Path ${env:ProgramFiles(x86)} "Microsoft\Edge\Application\msedge.exe"
    Join-Path $env:ProgramFiles "Microsoft\Edge\Application\msedge.exe"
  ) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1

  $chrome = @(
    Join-Path ${env:ProgramFiles} "Google\Chrome\Application\chrome.exe"
    Join-Path ${env:ProgramFiles(x86)} "Google\Chrome\Application\chrome.exe"
  ) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1

  if ($edge) {
    Start-Process -FilePath $edge -ArgumentList "--app=$Url"
    return
  }

  if ($chrome) {
    Start-Process -FilePath $chrome -ArgumentList "--app=$Url"
    return
  }

  Start-Process $Url
}

try {
  Remove-Item -Path $ErrorLog -Force -ErrorAction SilentlyContinue
  if (Test-CareerBot) {
    $runningVersion = Get-CareerBotVersion
    if (-not $runningVersion -or $runningVersion -ne $ExpectedVersion) {
      Stop-PreviousCareerBot
      Start-CareerBotServer
    }
  }

  if (-not (Test-CareerBot)) {
    Start-CareerBotServer
  }

  Open-AppWindow
} catch {
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $ErrorLog) | Out-Null
  $message = "$(Get-Date -Format s) $($_.Exception.Message)"
  Set-Content -Path $ErrorLog -Value $message -Encoding utf8
  Write-Host $message -ForegroundColor Red
  exit 1
}
