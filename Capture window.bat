@echo off
REM Double-click to pick a window and capture it macOS-style.
cd /d "%~dp0"
python -m macshot --open
if errorlevel 1 pause
