@echo off
REM Freya TUI Launcher
cd /d "%~dp0"
call freya_env\Scripts\activate.bat
python run_tui.py
pause
