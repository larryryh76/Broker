$ErrorActionPreference = "SilentlyContinue"

# Use GITHUB_WORKSPACE if available, else current directory
$workspace = $env:GITHUB_WORKSPACE
if (-not $workspace) { $workspace = Get-Location }

$installPath = "$workspace\terminal"
$exePath = "$installPath\terminal64.exe"
$dataPath = "$installPath"
$logPath = "$installPath\MQL5\Logs"
$originFile = "$installPath\origin.txt"

Write-Host "=== MT5 DEVOPS-HARDENED PRE-LAUNCH ==="

# 🔥 Kill all existing processes
taskkill /F /IM terminal64.exe 2>$null
taskkill /F /IM metaeditor64.exe 2>$null

Start-Sleep -Seconds 3

# 🔥 Create clean folders
if (!(Test-Path $logPath)) {
    New-Item -ItemType Directory -Force -Path $logPath | Out-Null
}

# 🔥 Generate LOBOTOMIZED config
$startupIni = @"
[Common]
Login=$($env:MT5_LOGIN)
Password=$($env:MT5_PASSWORD)
Server=$($env:MT5_SERVER)
CertConfirm=1

[Experts]
AllowLiveTrading=1
Enabled=1

[Charts]
MaxBars=100

[Startup]
EnableNews=0
EnableSound=0

[Tester]
AllowOptimization=0
"@

$startupIni | Out-File -Encoding ASCII "$installPath\startup.ini"

Write-Host "Config injected into $installPath\startup.ini"

# Function to launch and watch
function Launch-And-Watch {
    param([string]$extraArgs = "")

    Write-Host "Launching MT5... $extraArgs"
    Start-Process -FilePath $exePath -ArgumentList "/portable /config:startup.ini $extraArgs" -WorkingDirectory $installPath

    $timeout = 90
    $elapsed = 0
    while ($elapsed -lt $timeout) {
        $logs = Get-ChildItem -Path $logPath -Filter *.log -ErrorAction SilentlyContinue
        $originExists = Test-Path $originFile

        if ($logs -or $originExists) {
            Write-Host "MT5 INITIALIZATION DETECTED (Logs: $(!!$logs), Origin: $originExists)."
            Write-Host "TERMINAL READY."
            return $true
        }

        Start-Sleep -Seconds 5
        $elapsed += 5
        Write-Host "Waiting for logs or origin.txt... ($elapsed sec)"
    }
    return $false
}

$success = Launch-And-Watch

# 🔥 Retry with /clear if no success
if (-not $success) {
    Write-Host "No initialization detected. Retrying with /clear..."
    taskkill /F /IM terminal64.exe 2>$null
    Start-Sleep -Seconds 5
    $success = Launch-And-Watch "/clear"
}

if ($success) {
    # 🔥 Final signal file
    New-Item -Path "$installPath\READY.flag" -ItemType File -Force | Out-Null
    Write-Host "=== PRE-LAUNCH COMPLETE SUCCESS ==="
} else {
    Write-Host "=== PRE-LAUNCH FAILED TO INITIALIZE ===."
    exit 1
}
