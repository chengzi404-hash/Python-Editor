param(
    [string]$OutputDir = "release"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot
$DistDir = Join-Path $ProjectRoot "dist"
$ReleaseDir = Join-Path $ProjectRoot $OutputDir

$ESC = [char]27
$RED = "$ESC[91m"
$GREEN = "$ESC[92m"
$YELLOW = "$ESC[93m"
$BLUE = "$ESC[94m"
$MAGENTA = "$ESC[95m"
$CYAN = "$ESC[96m"
$WHITE = "$ESC[97m"
$BG_RED = "$ESC[41m"
$BG_GREEN = "$ESC[42m"
$BG_YELLOW = "$ESC[43m"
$BG_BLUE = "$ESC[44m"
$BG_MAGENTA = "$ESC[45m"
$BOLD = "$ESC[1m"
$DIM = "$ESC[2m"
$UNDERLINE = "$ESC[4m"
$RESET = "$ESC[0m"

$JOBS = @(
    @{ Num = 1; Name = "Checking"; Desc = "Checking virtual environment" },
    @{ Num = 2; Name = "Installing"; Desc = "Installing PyInstaller" },
    @{ Num = 3; Name = "Cleaning"; Desc = "Cleaning previous build" },
    @{ Num = 4; Name = "Compiling"; Desc = "Running PyInstaller" },
    @{ Num = 5; Name = "Copying"; Desc = "Copying executable" },
    @{ Num = 6; Name = "Copying"; Desc = "Copying language files" },
    @{ Num = 7; Name = "Copying"; Desc = "Copying runtime dependencies" }
)

$TOTAL_JOBS = $JOBS.Count

function Write-Banner {
    param([string]$Text)
    $line = "=" * 60
    Write-Host ""
    Write-Host "$CYAN$line$RESET"
    Write-Host "$BOLD$WHITE  $Text$RESET"
    Write-Host "$CYAN$line$RESET"
    Write-Host ""
}

function Write-JobHeader {
    param([int]$Num, [string]$Name, [string]$Desc)
    $totalWidth = 60
    $prefix = "========="
    $suffix = "========="
    $middle = "= JOB $Num/$TOTAL_JOBS $Name "
    $remaining = $totalWidth - $prefix.Length - $suffix.Length - $middle.Length
    if ($remaining -gt 0) {
        $header = "$prefix$middle$('=' * $remaining)$suffix"
    } else {
        $header = "$prefix$middle$suffix"
    }
    Write-Host ""
    Write-Host "$YELLOW$BOLD$header$RESET"
    Write-Host "$DIM$Desc$RESET"
    Write-Host ""
}

function Write-Step {
    param([string]$Text, [string]$Color = $WHITE)
    Write-Host "  $Color$Text$RESET"
}

function Write-Success {
    param([string]$Text)
    Write-Host "  $GREEN$BOLD$Text$RESET"
}

function Write-Warning {
    param([string]$Text)
    Write-Host "  $YELLOW$BOLD$Text$RESET"
}

function Write-Error {
    param([string]$Text)
    Write-Host "  $RED$BOLD$Text$RESET"
}

function Invoke-Job {
    param(
        [int]$Num,
        [string]$Name,
        [string]$Desc,
        [scriptblock]$Action
    )
    Write-Host "$ESC[?25l"
    Write-JobHeader -Num $Num -Name $Name -Desc $Desc
    & $Action
    Write-Host "$ESC[?25h"
}

Write-Host "$ESC[?25l"
Write-Banner "Python Editor Build Script"

$jobNum = 0

Invoke-Job -Num (++$jobNum) -Name "Checking" -Desc "Checking virtual environment..." -Action {
    if (-not (Test-Path ".venv")) {
        Write-Warning "Virtual environment not found. Run: uv sync"
        Write-Host "$ESC[?25h"
        exit 1
    }
    Write-Success "Virtual environment found"
}

Invoke-Job -Num (++$jobNum) -Name "Installing" -Desc "Checking/Installing PyInstaller..." -Action {
    $PyInstallerVersion = & ".venv\Scripts\python.exe" -m PyInstaller --version 2>$null
    if (-not $PyInstallerVersion) {
        Write-Step "Installing PyInstaller..." -Color $YELLOW
        & ".venv\Scripts\python.exe" -m pip install pyinstaller>=6.11.0 pyinstaller-hooks-contrib>=2024.10
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to install PyInstaller"
            Write-Host "$ESC[?25h"
            exit 1
        }
        Write-Success "PyInstaller installed"
    } else {
        Write-Success "PyInstaller already installed ($PyInstallerVersion)"
    }
}

Invoke-Job -Num (++$jobNum) -Name "Cleaning" -Desc "Cleaning previous build artifacts..." -Action {
    if (Test-Path "build") {
        Remove-Item -Recurse -Force "build"
        Write-Step "Removed build/" -Color $DIM
    }
    if (Test-Path $DistDir) {
        Remove-Item -Recurse -Force $DistDir
        Write-Step "Removed dist/" -Color $DIM
    }
    Write-Success "Clean complete"
}

Invoke-Job -Num (++$jobNum) -Name "Compiling" -Desc "Running PyInstaller..." -Action {
    Write-Step "Building PythonEditor.exe..." -Color $CYAN
    & ".venv\Scripts\python.exe" -m PyInstaller PythonEditor.spec --noconfirm --clean 2>&1 | ForEach-Object {
        if ($_ -match "error|failed|warning") {
            Write-Host "    $YELLOW$_$RESET"
        } else {
            Write-Host "    $DIM$_$RESET"
        }
    }
    if ($LASTEXITCODE -ne 0) {
        Write-Error "PyInstaller failed"
        Write-Host "$ESC[?25h"
        exit 1
    }
    Write-Success "PyInstaller completed"
}

Invoke-Job -Num (++$jobNum) -Name "Copying" -Desc "Copying executable to release..." -Action {
    $ExePath = Join-Path $DistDir "PythonEditor.exe"
    if (-not (Test-Path $ExePath)) {
        Write-Error "Build failed: exe not found at $ExePath"
        Write-Host "$ESC[?25h"
        exit 1
    }

    if (Test-Path $ReleaseDir) {
        Remove-Item -Recurse -Force $ReleaseDir
    }
    New-Item -ItemType Directory -Path $ReleaseDir | Out-Null
    Copy-Item $ExePath -Destination $ReleaseDir
    Write-Success "Copied PythonEditor.exe"
}

Invoke-Job -Num (++$jobNum) -Name "Copying" -Desc "Copying language files..." -Action {
    $LangSource = Join-Path $ProjectRoot "data\i18n\locales"
    $LangDest = Join-Path $ReleaseDir "modules\i18n\locales"
    if (Test-Path $LangSource) {
        New-Item -ItemType Directory -Path $LangDest -Force | Out-Null
        $files = Get-ChildItem (Join-Path $LangSource "*.json")
        Copy-Item (Join-Path $LangSource "*.json") -Destination $LangDest
        Write-Success "Copied $($files.Count) language files"
    } else {
        Write-Warning "No language files found"
    }
}

Invoke-Job -Num (++$jobNum) -Name "Copying" -Desc "Copying runtime dependencies (tcl/tk)..." -Action {
    $VenvScripts = Join-Path $ProjectRoot ".venv\Scripts"
    $tclDir = Join-Path $VenvScripts "tcl"
    $tkDir = Join-Path $VenvScripts "tk"
    $tk86t = Join-Path $VenvScripts "tk86t.dll"
    $tcl86t = Join-Path $VenvScripts "tcl86t.dll"
    $copied = 0

    if (Test-Path $tk86t) {
        Copy-Item $tk86t -Destination $ReleaseDir -Force
        $copied++
    }
    if (Test-Path $tcl86t) {
        Copy-Item $tcl86t -Destination $ReleaseDir -Force
        $copied++
    }
    if (Test-Path $tclDir) {
        Copy-Item $tclDir -Destination $ReleaseDir -Recurse -Force
        $copied++
    }
    if (Test-Path $tkDir) {
        Copy-Item $tkDir -Destination $ReleaseDir -Recurse -Force
        $copied++
    }
    Write-Success "Copied $copied runtime dependencies"
}

Write-Host ""
Write-Banner "Build Complete"

Write-Host "$GREEN$BOLD  PythonEditor.exe built successfully!$RESET"
Write-Host ""
Write-Host "  $WHITE$UNDERLINE$ReleaseDir\PythonEditor.exe$RESET"
Write-Host ""

Write-Host "$CYAN  Release directory contents:$RESET"
Get-ChildItem $ReleaseDir | ForEach-Object {
    if ($_.PSIsContainer) {
        Write-Host "  $WHITE$($_.Name)/$RESET"
        Get-ChildItem $_.FullName | Select-Object -First 5 | ForEach-Object {
            Write-Host "    $DIM$($_.Name)$RESET"
        }
        if ((Get-ChildItem $_.FullName).Count -gt 5) {
            Write-Host "    $DIM...$RESET"
        }
    } else {
        Write-Host "  $WHITE$($_.Name)$RESET"
    }
}
Write-Host ""
Write-Host "$ESC[?25h"
