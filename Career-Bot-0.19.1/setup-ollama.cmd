@echo off
setlocal

set "OLLAMA_EXE=%LOCALAPPDATA%\Programs\Ollama\ollama.exe"

if not exist "%OLLAMA_EXE%" (
  echo Ollama is not installed yet.
  echo The official download page will open now.
  echo Install Ollama, then run this file again.
  start "" "https://ollama.com/download/windows"
  pause
  exit /b 0
)

echo Starting Ollama...
start "" "%LOCALAPPDATA%\Programs\Ollama\ollama app.exe"
timeout /t 3 /nobreak >nul

echo Downloading qwen3:8b. This is about 5 GB and only needs to be done once.
"%OLLAMA_EXE%" pull qwen3:8b
if errorlevel 1 (
  echo.
  echo The model could not be downloaded. Check the internet connection and run this file again.
  pause
  exit /b 1
)

echo.
echo Ollama and qwen3:8b are ready for Career Bot.
pause
