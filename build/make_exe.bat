@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0make_exe.ps1"
if errorlevel 1 (
  echo.
  echo BUILD FAILED. See messages above.
  exit /b 1
)
echo.
echo ============================================================
echo  heka2abf-gui.exe is ready in the dist\ folder.
echo ============================================================
endlocal