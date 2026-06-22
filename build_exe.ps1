param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

if ($Clean) {
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue "build", "Macshot.spec"
}

$ExePath = Join-Path $ProjectRoot "dist\Macshot.exe"
if (Test-Path $ExePath) {
    try {
        Remove-Item -Force $ExePath
    } catch {
        Write-Error "Could not replace $ExePath. Close any running Macshot.exe instance and try again."
        exit 1
    }
}

python -m pip install -r requirements.txt

python -m PyInstaller `
    --onefile `
    --windowed `
    --name Macshot `
    --hidden-import pystray._win32 `
    --hidden-import PIL.Image `
    --hidden-import PIL.ImageDraw `
    --hidden-import win32timezone `
    --noconfirm `
    macshot_launcher.py

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Built: $ProjectRoot\dist\Macshot.exe"
