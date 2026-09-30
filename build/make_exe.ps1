# make_exe.ps1
# Build the heka2abf GUI exe via PyInstaller.
#
# Usage (from project root):
#   powershell -ExecutionPolicy Bypass -File build\make_exe.ps1                # default: onefile
#   powershell -ExecutionPolicy Bypass -File build\make_exe.ps1 -Mode onefile  # single .exe
#   powershell -ExecutionPolicy Bypass -File build\make_exe.ps1 -Mode onedir   # folder, faster startup
#
# Outputs:
#   onefile -> dist\heka2abf-gui.exe                        (single file,  ~23 MB)
#   onedir  -> dist\heka2abf-gui\heka2abf-gui.exe           (folder,        ~50 MB)

param(
    [ValidateSet('onefile','onedir')]
    [string]$Mode = 'onefile'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$venvPy = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $venvPy)) {
  throw "venv missing at $venvPy — run install.bat first"
}

if ($Mode -eq 'onefile') {
  $spec = Join-Path $root 'build\heka2abf-gui.spec'
  $expected = Join-Path $root 'dist\heka2abf-gui.exe'
  $description = "single-file .exe"
} else {
  $spec = Join-Path $root 'build\heka2abf-gui-onedir.spec'
  $expected = Join-Path $root 'dist\heka2abf-gui\heka2abf-gui.exe'
  $description = "onedir folder"
}

Write-Host "[1/3] Building $description ..."
Write-Host "       spec: $spec"

Write-Host "[2/3] Verifying dependencies ..."
& $venvPy -c "import numpy, heka_reader; print('       numpy', numpy.__version__, ' heka_reader OK')"

Write-Host "[3/3] Running PyInstaller ..."
& $venvPy -m PyInstaller $spec --noconfirm --clean 2>&1 | Tee-Object -FilePath (Join-Path $root 'build\pyinstaller.log') | Out-Null

if (-not (Test-Path $expected)) {
  throw "Build finished but $expected not found"
}

if ($Mode -eq 'onefile') {
  $sizeMB = [math]::Round((Get-Item $expected).Length / 1MB, 1)
  Write-Host "DONE: $expected ($sizeMB MB)"
} else {
  $folder = Split-Path $expected -Parent
  $totalBytes = (Get-ChildItem $folder -Recurse | Measure-Object -Sum Length).Sum
  $sizeMB = [math]::Round($totalBytes / 1MB, 1)
  Write-Host "DONE: $folder\ ($sizeMB MB total)"
  Write-Host "       launch: $expected"
  Write-Host "       (zip the folder if you want to distribute)"
}

Write-Host ""
Write-Host "Smoke-test:"
Write-Host "  Start-Process -FilePath '$expected' -PassThru | Out-Null"