@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set "PYW=pythonw.exe"
if exist ".venv\Scripts\pythonw.exe" set "PYW=.venv\Scripts\pythonw.exe"
if exist "..\.venv\Scripts\pythonw.exe" set "PYW=..\.venv\Scripts\pythonw.exe"
if not exist "%PYW%" set "PYW=python.exe"
start "heka2abf" "%PYW%" "%~dp0heka2abf\gui.py"
endlocal