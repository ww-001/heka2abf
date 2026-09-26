# make_windows_bundle.ps1
# Helper for make_windows_bundle.bat: compresses a directory into a zip.
# Paths are passed as command-line arguments (no embedded %VARS% inside
# the PowerShell code, which would NOT be expanded by PowerShell).

param(
    [Parameter(Mandatory = $true)][string]$StageDir,
    [Parameter(Mandatory = $true)][string]$ZipPath
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path $StageDir)) {
    throw "Stage directory not found: $StageDir"
}

Add-Type -AssemblyName System.IO.Compression.FileSystem

# Write to a .tmp file first, then atomic rename — so a half-written zip
# never appears at the final path.
$tmp = "$ZipPath.tmp"
if (Test-Path $tmp) { Remove-Item $tmp -Force }

# includeBaseDirectory = $true makes the staging dir name (e.g. "heka2abf")
# become the root folder in the zip, so the user unzips and sees a clean
# `heka2abf/` folder instead of files scattered at the archive root.
[System.IO.Compression.ZipFile]::CreateFromDirectory(
    (Resolve-Path $StageDir),
    $tmp,
    [System.IO.Compression.CompressionLevel]::Optimal,
    $true
)

Move-Item $tmp $ZipPath -Force
Write-Host "ZIP created: $ZipPath"