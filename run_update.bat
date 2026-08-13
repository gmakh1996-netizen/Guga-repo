@echo off
chcp 65001 >nul
REM Movie World - daily auto-update (run by Scheduled Task).
REM Imports the newest ge_movies*.json from Downloads - only NEW films.
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
".venv\Scripts\python.exe" update.py
