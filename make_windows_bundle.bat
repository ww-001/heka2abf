@echo off
REM ============================================================
REM Build a self-contained Windows distribution ZIP for heka2abf.
REM
REM Usage:  make_windows_bundle.bat
REM
REM What it does:
REM   1. Verifies .venv/ exists (run install.bat first if not).
REM   2. Creates a staging folder under dist-bundle-stage/.
REM   3. Copies project files + the bundled .venv/ into staging/heka2abf/.
REM   4. Excludes dev artifacts (.git, __pycache__, tests/*.abf, etc.).
REM   5. Compresses the staged tree into heka2abf_windows_v<VERSION>.zip.
REM
REM The ZIP is laid out so that unzipping creates a single "heka2abf/" folder
REM containing run_gui.bat at the top level — matching what install.bat expects
REM and what WINDOWS_BUNDLE_README.md documents.
REM ============================================================

setlocal EnableDelayedExpansion
cd /d "%~dp0"

REM --- Read version from heka2abf/__init__.py ---
set "VERSION=0.0.0"
for /f "tokens=2 delims== " %%V in ('findstr /b /c:"__version__" heka2abf\__init__.py') do (
    set "VERSION=%%V"
    set "VERSION=!VERSION:"=!"
)
echo [1/5] Detected version: !VERSION!

REM --- Verify .venv exists ---
echo [2/5] Verifying .venv\Scripts\python.exe ...
if not exist ".venv\Scripts\python.exe" (
    echo ERROR: .venv\Scripts\python.exe not found.
    echo Run install.bat first to create the virtual environment.
    exit /b 1
)

REM --- Pre-compute absolute paths (exported via SETX-free env-vars to PowerShell) ---
set "PROJECT_ROOT=%CD%"
set "STAGE=%PROJECT_ROOT%\dist-bundle-stage"
set "STAGE_HEKA=%STAGE%\heka2abf"
set "ZIPNAME=%PROJECT_ROOT%\heka2abf_windows_v!VERSION!.zip"

echo [3/5] Staging into %STAGE_HEKA% ...
if exist "%STAGE%" rmdir /s /q "%STAGE%"
mkdir "%STAGE_HEKA%"

REM --- Copy project files (Windows 10/11 robocopy: NO colon after /XD) ---
echo       Copying source files ...
REM --- Copy project files ---
REM robocopy treats bare directory names as single files (not directories)
REM so we MUST use a wildcard (e.g. "heka2abf\*") or recursive /MIR for full
REM directory contents.  We use one robocopy call per directory + one
REM consolidated call for loose top-level files.
echo       Copying source files ...
robocopy "%PROJECT_ROOT%\heka2abf"    "%STAGE_HEKA%\heka2abf"    /E /NFL /NDL /NJH /NJS /NC /NS /NP >nul
if errorlevel 8 (echo ERROR: copy heka2abf\ failed code !errorlevel! & exit /b 1)
robocopy "%PROJECT_ROOT%\tests"      "%STAGE_HEKA%\tests"      /E /NFL /NDL /NJH /NJS /NC /NS /NP >nul
if errorlevel 8 (echo ERROR: copy tests\ failed code !errorlevel! & exit /b 1)
robocopy "%PROJECT_ROOT%\reference"  "%STAGE_HEKA%\reference"  /E /NFL /NDL /NJH /NJS /NC /NS /NP >nul
if errorlevel 8 (echo ERROR: copy reference\ failed code !errorlevel! & exit /b 1)
robocopy "%PROJECT_ROOT%\third_party" "%STAGE_HEKA%\third_party" /E /NFL /NDL /NJH /NJS /NC /NS /NP >nul
if errorlevel 8 (echo ERROR: copy third_party\ failed code !errorlevel! & exit /b 1)
robocopy "%PROJECT_ROOT%\tools"      "%STAGE_HEKA%\tools"      /E /NFL /NDL /NJH /NJS /NC /NS /NP >nul
if errorlevel 8 (echo ERROR: copy tools\ failed code !errorlevel! & exit /b 1)
robocopy "%PROJECT_ROOT%\docs"       "%STAGE_HEKA%\docs"       /E /NFL /NDL /NJH /NJS /NC /NS /NP >nul
if errorlevel 8 (echo ERROR: copy docs\ failed code !errorlevel! & exit /b 1)
REM Loose top-level files (single-file copy, no recursion needed)
copy /y "%PROJECT_ROOT%\install.bat"            "%STAGE_HEKA%\install.bat"            >nul || (echo ERROR: copy install.bat & exit /b 1)
copy /y "%PROJECT_ROOT%\run_gui.bat"            "%STAGE_HEKA%\run_gui.bat"            >nul || (echo ERROR: copy run_gui.bat & exit /b 1)
copy /y "%PROJECT_ROOT%\run_gui_console.bat"    "%STAGE_HEKA%\run_gui_console.bat"    >nul || (echo ERROR: copy run_gui_console.bat & exit /b 1)
copy /y "%PROJECT_ROOT%\install.sh"             "%STAGE_HEKA%\install.sh"             >nul || (echo ERROR: copy install.sh & exit /b 1)
copy /y "%PROJECT_ROOT%\run_gui.sh"             "%STAGE_HEKA%\run_gui.sh"             >nul || (echo ERROR: copy run_gui.sh & exit /b 1)
copy /y "%PROJECT_ROOT%\make_windows_bundle.bat" "%STAGE_HEKA%\make_windows_bundle.bat" >nul || (echo ERROR: copy make_windows_bundle.bat & exit /b 1)
copy /y "%PROJECT_ROOT%\WINDOWS_BUNDLE_README.md" "%STAGE_HEKA%\WINDOWS_BUNDLE_README.md" >nul || (echo ERROR: copy WINDOWS_BUNDLE_README.md & exit /b 1)
copy /y "%PROJECT_ROOT%\README.md"     "%STAGE_HEKA%\README.md"     >nul || (echo ERROR: copy README.md & exit /b 1)
copy /y "%PROJECT_ROOT%\LICENSE"       "%STAGE_HEKA%\LICENSE"       >nul || (echo ERROR: copy LICENSE & exit /b 1)
copy /y "%PROJECT_ROOT%\CHANGELOG.md"  "%STAGE_HEKA%\CHANGELOG.md"  >nul || (echo ERROR: copy CHANGELOG.md & exit /b 1)
copy /y "%PROJECT_ROOT%\CITATION.cff"  "%STAGE_HEKA%\CITATION.cff"  >nul || (echo ERROR: copy CITATION.cff & exit /b 1)
copy /y "%PROJECT_ROOT%\MANIFEST.in"   "%STAGE_HEKA%\MANIFEST.in"   >nul || (echo ERROR: copy MANIFEST.in & exit /b 1)
copy /y "%PROJECT_ROOT%\requirements.txt" "%STAGE_HEKA%\requirements.txt" >nul || (echo ERROR: copy requirements.txt & exit /b 1)
copy /y "%PROJECT_ROOT%\pyproject.toml" "%STAGE_HEKA%\pyproject.toml" >nul || (echo ERROR: copy pyproject.toml & exit /b 1)
copy /y "%PROJECT_ROOT%\.gitignore"    "%STAGE_HEKA%\.gitignore"    >nul || (echo ERROR: copy .gitignore & exit /b 1)
if exist "%PROJECT_ROOT%\.gitattributes" copy /y "%PROJECT_ROOT%\.gitattributes" "%STAGE_HEKA%\.gitattributes" >nul
REM robocopy exit codes 0..1 = success, 2..7 = files copied (no failure),
REM 8+ = real failure. We tolerate up to 7.
if errorlevel 8 (
    echo ERROR: robocopy source copy failed with code !errorlevel!.
    exit /b 1
)

REM --- Copy the bundled .venv ---
echo       Copying bundled .venv ...  ^(may take a minute~)
robocopy "%PROJECT_ROOT%\.venv" "%STAGE_HEKA%\.venv" /E /NFL /NDL /NJH /NJS /NC /NS /NP >nul
if errorlevel 8 (
    echo ERROR: robocopy .venv copy failed with code !errorlevel!.
    exit /b 1
)

REM --- Verify staging ---
echo [4/5] Verifying staging contents ...
if not exist "%STAGE_HEKA%\.venv\Scripts\python.exe" (
    echo ERROR: staged .venv missing python.exe.
    exit /b 1
)
if not exist "%STAGE_HEKA%\.venv\Lib\site-packages\numpy" (
    echo ERROR: staged .venv missing numpy.
    exit /b 1
)
if not exist "%STAGE_HEKA%\.venv\Lib\site-packages\heka_reader.py" (
    echo ERROR: staged .venv missing heka_reader.py.
    exit /b 1
)
if not exist "%STAGE_HEKA%\run_gui.bat" (
    echo ERROR: staged run_gui.bat missing.
    exit /b 1
)

REM --- Zip it ---
echo [5/5] Creating %ZIPNAME% ...
if exist "%ZIPNAME%" del "%ZIPNAME%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0make_windows_bundle.ps1" -StageDir "%STAGE_HEKA%" -ZipPath "%ZIPNAME%"
if errorlevel 1 (
    echo ERROR: ZIP creation failed.
    exit /b 1
)

REM --- Clean up staging (set KEEP_STAGE=1 to skip cleanup for debugging) ---
if not defined KEEP_STAGE rmdir /s /q "%STAGE%"

echo.
echo ============================================================
echo DONE: heka2abf_windows_v!VERSION!.zip
echo.
echo Upload to GitHub release:
echo   gh release upload v!VERSION! heka2abf_windows_v!VERSION!.zip
echo ============================================================
endlocal