@echo off
REM Freya Main Program Launcher
cd /d "%~dp0"
call freya_env\Scripts\activate.bat
python main.py %*
