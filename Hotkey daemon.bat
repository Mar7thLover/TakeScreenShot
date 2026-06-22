@echo off
REM Runs in the background. Press Ctrl+Shift+S anytime to capture a window.
REM Put a shortcut to this file in shell:startup to launch it at login.
cd /d "%~dp0"
python -m macshot --hotkey --combo ctrl+shift+s
pause
