@echo off
set "EXTENSION_DIR=%~dp0hh-career-bot-extension"
start "" explorer.exe "%EXTENSION_DIR%"
start "" msedge.exe "edge://extensions/"
echo.
echo 1. Turn on Developer mode in Edge extensions.
echo 2. Click Load unpacked.
echo 3. Select the folder opened in Explorer: hh-career-bot-extension
echo 4. Refresh the hh.ru page.
echo.
pause
