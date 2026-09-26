@echo off
setlocal
cd /d "%~dp0"
set "PY=python.exe"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
if exist "..\.venv\Scripts\python.exe" set "PY=..\.venv\Scripts\python.exe"
"%PY%" "%~dp0heka2abf\gui.py"
endlocal
