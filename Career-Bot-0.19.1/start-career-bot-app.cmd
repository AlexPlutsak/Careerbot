@echo off
setlocal

set "CAREER_BOT_ROOT=%~dp0"
set "CAREER_BOT_LAUNCHER=%CAREER_BOT_ROOT%scripts\launch-career-bot.ps1"
set "CAREER_BOT_CONFIG=%~dp0career-bot-location.txt"

if not exist "%CAREER_BOT_LAUNCHER%" (
  if exist "%CAREER_BOT_CONFIG%" set /p CAREER_BOT_ROOT=<"%CAREER_BOT_CONFIG%"
  if defined CAREER_BOT_ROOT set "CAREER_BOT_LAUNCHER=%CAREER_BOT_ROOT%scripts\launch-career-bot.ps1"
)

if not exist "%CAREER_BOT_LAUNCHER%" (
  for /f "usebackq delims=" %%P in (`powershell.exe -NoProfile -Command "$roots=@((Join-Path $env:USERPROFILE 'OneDrive'),(Join-Path $env:USERPROFILE 'Desktop'),(Join-Path $env:USERPROFILE 'Documents'),(Join-Path $env:USERPROFILE 'Downloads')); foreach($base in ($roots | Where-Object {Test-Path $_})) { Get-ChildItem -LiteralPath $base -Filter 'launch-career-bot.ps1' -File -Recurse -ErrorAction SilentlyContinue | Where-Object { $_.Directory.Name -eq 'scripts' -and (Test-Path (Join-Path $_.Directory.Parent.FullName 'career_bot\server.py')) } | Select-Object -First 1 -ExpandProperty FullName; if($?) { break } }"`) do (
    set "CAREER_BOT_LAUNCHER=%%P"
  )
)

if not exist "%CAREER_BOT_LAUNCHER%" (
  for /f "usebackq delims=" %%P in (`powershell.exe -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms; $dialog=New-Object System.Windows.Forms.FolderBrowserDialog; $dialog.Description='Выберите папку Career Bot'; if($dialog.ShowDialog() -eq 'OK' -and (Test-Path (Join-Path $dialog.SelectedPath 'scripts\launch-career-bot.ps1'))) { (Resolve-Path $dialog.SelectedPath).Path }"`) do (
    set "CAREER_BOT_ROOT=%%P\"
    set "CAREER_BOT_LAUNCHER=%%P\scripts\launch-career-bot.ps1"
    >"%CAREER_BOT_CONFIG%" echo %%P
  )
)

if not exist "%CAREER_BOT_LAUNCHER%" (
  echo.
  echo Career Bot project was not found or was not selected.
  pause
  exit /b 1
)

for %%P in ("%CAREER_BOT_LAUNCHER%") do set "CAREER_BOT_ROOT=%%~dpP..\"
cd /d "%CAREER_BOT_ROOT%"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%CAREER_BOT_LAUNCHER%"
if errorlevel 1 (
  echo.
  echo Career Bot failed to start. See "%CAREER_BOT_ROOT%data\launcher-error.log"
  pause
)
