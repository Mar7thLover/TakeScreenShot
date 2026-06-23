param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

#region agent log
function Write-AgentLog {
    param(
        [string]$HypothesisId,
        [string]$Location,
        [string]$Message,
        [hashtable]$Data
    )
    $payload = @{
        sessionId = "26b04d"
        runId = "build-debug"
        hypothesisId = $HypothesisId
        location = $Location
        message = $Message
        data = $Data
        timestamp = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
    } | ConvertTo-Json -Compress -Depth 6
    Add-Content -Path (Join-Path $ProjectRoot "debug-26b04d.log") -Value $payload -Encoding UTF8
}
Write-AgentLog "H1,H2,H3,H4,H5" "build_exe.ps1:10" "build script started" @{
    projectRoot = $ProjectRoot
    clean = [bool]$Clean
    python = (Get-Command python -ErrorAction SilentlyContinue).Source
}
#endregion

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

# Native commands (python/pip/pyinstaller) write progress and notices to stderr.
# Under $ErrorActionPreference = "Stop", PowerShell 5.1 turns those stderr lines
# into terminating NativeCommandErrors, aborting the build even on exit code 0.
# Switch to Continue here; correctness is enforced via explicit $LASTEXITCODE checks.
$ErrorActionPreference = "Continue"

#region agent log
$PipInstallOutput = python -m pip install -r requirements.txt 2>&1
$PipInstallExitCode = $LASTEXITCODE
Write-AgentLog "H3,H4" "build_exe.ps1:44" "pip install completed" @{
    exitCode = $PipInstallExitCode
    output = ($PipInstallOutput -join "`n")
}
if ($PipInstallExitCode -ne 0) {
    exit $PipInstallExitCode
}
$PyInstallerVersionOutput = python -m PyInstaller --version 2>&1
Write-AgentLog "H1,H3,H5" "build_exe.ps1:53" "pyinstaller version checked" @{
    exitCode = $LASTEXITCODE
    output = ($PyInstallerVersionOutput -join "`n")
}
#endregion

#region agent log
Write-AgentLog "H1,H2" "build_exe.ps1:61" "pyinstaller invocation about to run" @{
    args = @("--onefile", "--windowed", "--name", "Macshot", "--hidden-import", "pystray._win32", "--hidden-import", "PIL.Image", "--hidden-import", "PIL.ImageDraw", "--hidden-import", "win32timezone", "--noconfirm", "macshot_launcher.py")
}
$PyInstallerOutput = python -m PyInstaller `
    --onefile `
    --windowed `
    --name Macshot `
    --hidden-import pystray._win32 `
    --hidden-import PIL.Image `
    --hidden-import PIL.ImageDraw `
    --hidden-import win32timezone `
    --noconfirm `
    macshot_launcher.py 2>&1
$PyInstallerExitCode = $LASTEXITCODE
Write-AgentLog "H1,H2,H3,H5" "build_exe.ps1:77" "pyinstaller invocation completed" @{
    exitCode = $PyInstallerExitCode
    output = ($PyInstallerOutput -join "`n")
}
#endregion

if ($PyInstallerExitCode -ne 0) {
    exit $PyInstallerExitCode
}

Write-Host ""
Write-Host "Built: $ProjectRoot\dist\Macshot.exe"
