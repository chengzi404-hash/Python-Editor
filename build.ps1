param(
    [string]$OutputDir = "release"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot
$DistDir = Join-Path $ProjectRoot "dist"
$ReleaseDir = Join-Path $ProjectRoot $OutputDir

Write-Host "Building Python Editor for Windows..." -ForegroundColor Cyan

if (-not (Test-Path ".venv")) {
    Write-Host "Virtual environment not found. Run: uv sync" -ForegroundColor Red
    exit 1
}

$PyInstallerVersion = & ".venv\Scripts\python.exe" -m PyInstaller --version 2>$null
if (-not $PyInstallerVersion) {
    Write-Host "Installing PyInstaller..." -ForegroundColor Yellow
    & ".venv\Scripts\python.exe" -m pip install pyinstaller>=6.11.0 pyinstaller-hooks-contrib>=2024.10
}

if (Test-Path "build") {
    Remove-Item -Recurse -Force "build"
}

Write-Host "Running PyInstaller..." -ForegroundColor Yellow
& ".venv\Scripts\python.exe" -m PyInstaller PythonEditor.spec --noconfirm --clean

$ExePath = Join-Path $DistDir "PythonEditor.exe"
if (-not (Test-Path $ExePath)) {
    Write-Host "Build failed: exe not found" -ForegroundColor Red
    exit 1
}

if (Test-Path $ReleaseDir) {
    Remove-Item -Recurse -Force $ReleaseDir
}
New-Item -ItemType Directory -Path $ReleaseDir | Out-Null

Write-Host "Copying files to $OutputDir..." -ForegroundColor Yellow
Copy-Item $ExePath -Destination $ReleaseDir

$LangSource = Join-Path $ProjectRoot "data\i18n\locales"
$LangDest = Join-Path $ReleaseDir "modules\i18n\locales"
if (Test-Path $LangSource) {
    New-Item -ItemType Directory -Path $LangDest -Force | Out-Null
    Copy-Item (Join-Path $LangSource "*.json") -Destination $LangDest
}

$VenvScripts = Join-Path $ProjectRoot ".venv\Scripts"
$tclDir = Join-Path $VenvScripts "tcl"
$tkDir = Join-Path $VenvScripts "tk"

$tk86t = Join-Path $VenvScripts "tk86t.dll"
$tcl86t = Join-Path $VenvScripts "tcl86t.dll"

if (Test-Path $tk86t) {
    Copy-Item $tk86t -Destination $ReleaseDir -Force
}
if (Test-Path $tcl86t) {
    Copy-Item $tcl86t -Destination $ReleaseDir -Force
}

if (Test-Path $tclDir) {
    $tclDest = Join-Path $ReleaseDir "tcl"
    Copy-Item $tclDir -Destination $ReleaseDir -Recurse -Force
}
if (Test-Path $tkDir) {
    $tkDest = Join-Path $ReleaseDir "tk"
    Copy-Item $tkDir -Destination $ReleaseDir -Recurse -Force
}

Write-Host ""
Write-Host "Build successful: $ReleaseDir\PythonEditor.exe" -ForegroundColor Green
Write-Host ""
Write-Host "Release directory contents:" -ForegroundColor Cyan
Get-ChildItem $ReleaseDir | ForEach-Object {
    if ($_.PSIsContainer) {
        Write-Host "  $($_.Name)/" -ForegroundColor White
        Get-ChildItem $_.FullName | Select-Object -First 5 | ForEach-Object {
            Write-Host "    $($_.Name)" -ForegroundColor Gray
        }
        if ((Get-ChildItem $_.FullName).Count -gt 5) {
            Write-Host "    ..." -ForegroundColor Gray
        }
    } else {
        Write-Host "  $($_.Name)" -ForegroundColor White
    }
}
