# start_pulse_daemon.ps1
#
# Single-command launcher for the PULSE Instagram daemon. Runs preflight
# checks, sets the production env, kills any stale daemons, and starts a
# fresh instance with logging to tmp/ig_daemon.log.
#
# Usage (from any PowerShell window):
#   .\scripts\start_pulse_daemon.ps1
#
# Optional flags:
#   -Headless     Run real Chrome in headless mode (default: visible window)
#   -PollMin N    Min seconds between polls (default 60)
#   -PollMax N    Max seconds between polls (default 120)

param(
    [switch]$Headless,
    [int]$PollMin = 60,
    [int]$PollMax = 120
)

$ErrorActionPreference = "Stop"
$repo = "C:\Users\User\CMO-Agent"
$venvPython = "C:\Users\User\Business-Empire-Agent\.venv\Scripts\python.exe"
$logPath = Join-Path $repo "tmp\ig_daemon.log"
$envPath = Join-Path $repo ".env.agents"
$chromeStandard = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$chromeAlt = "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"

Write-Host "=== PULSE Instagram Daemon Launcher ===" -ForegroundColor Cyan

# Preflight 1: venv Python exists
if (-not (Test-Path $venvPython)) {
    Write-Host "FAIL: venv Python not found at $venvPython" -ForegroundColor Red
    Write-Host "  Update the path at the top of this script." -ForegroundColor Yellow
    exit 1
}
Write-Host "OK: venv Python at $venvPython" -ForegroundColor Green

# Preflight 2: Chrome installed
if (Test-Path $chromeStandard) {
    Write-Host "OK: Chrome installed at $chromeStandard" -ForegroundColor Green
} elseif (Test-Path $chromeAlt) {
    Write-Host "OK: Chrome installed at $chromeAlt" -ForegroundColor Green
} else {
    Write-Host "WARNING: Chrome not found at standard paths." -ForegroundColor Yellow
    Write-Host "  Daemon will fall back to Playwright Chromium (likely to be bot-detected)." -ForegroundColor Yellow
    Write-Host "  Install Chrome from https://www.google.com/chrome/ for best results." -ForegroundColor Yellow
}

# Preflight 3: .env.agents has IG creds + PULSE secret
if (-not (Test-Path $envPath)) {
    Write-Host "FAIL: $envPath missing" -ForegroundColor Red
    exit 1
}
$envContent = Get-Content $envPath -Raw
$missing = @()
foreach ($key in @("INSTAGRAM_USERNAME", "INSTAGRAM_PASSWORD", "PULSE_WEBHOOK_SECRET", "PULSE_ACCOUNT_ID")) {
    if ($envContent -notmatch "(?m)^$key=.+") { $missing += $key }
}
if ($missing.Count -gt 0) {
    Write-Host "FAIL: missing env keys in .env.agents: $($missing -join ', ')" -ForegroundColor Red
    exit 1
}
Write-Host "OK: .env.agents has all required keys" -ForegroundColor Green

# Preflight 4: PULSE webhook reachable
Write-Host "Pinging PULSE..." -ForegroundColor Gray
try {
    $resp = Invoke-RestMethod -Uri "https://ig-setter-pro.vercel.app/api/accounts" -Method Get -TimeoutSec 10
    if ($resp.accounts -and $resp.accounts.Count -gt 0) {
        $a = $resp.accounts[0]
        Write-Host "OK: PULSE reachable; account @$($a.ig_username), auto_send=$($a.auto_send_enabled)" -ForegroundColor Green
    } else {
        Write-Host "WARN: PULSE responded but no accounts configured" -ForegroundColor Yellow
    }
} catch {
    Write-Host "FAIL: PULSE not reachable ($_)" -ForegroundColor Red
    exit 1
}

# Kill any stale daemon processes
$existing = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -like '*instagram_engine*' }
if ($existing) {
    Write-Host "Killing stale daemon(s):" -ForegroundColor Yellow
    foreach ($p in $existing) {
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
        Write-Host "  killed PID $($p.ProcessId)" -ForegroundColor Yellow
    }
    Start-Sleep -Seconds 2
}

# Rotate the log
if (Test-Path $logPath) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    Move-Item $logPath "$logPath.$stamp" -Force -ErrorAction SilentlyContinue
}

# Set production env
$env:IG_BROWSER_CHANNEL = "chrome"
if ($Headless) {
    $env:IG_HEADLESS = "1"
    Write-Host "Mode: HEADLESS (real Chrome, no visible window)" -ForegroundColor Cyan
} else {
    $env:IG_HEADLESS = "0"
    Write-Host "Mode: VISIBLE (real Chrome window will open on your desktop)" -ForegroundColor Cyan
}

# Launch
Write-Host ""
Write-Host "Starting daemon (poll every $PollMin-$PollMax seconds)..." -ForegroundColor Cyan
$proc = Start-Process -FilePath $venvPython `
    -ArgumentList "-u", "scripts/instagram_engine.py", "monitor-dms", "--poll-min", $PollMin, "--poll-max", $PollMax `
    -WorkingDirectory $repo `
    -RedirectStandardOutput $logPath `
    -RedirectStandardError "$logPath.err" `
    -PassThru `
    -WindowStyle Hidden

Write-Host ""
Write-Host "=== DAEMON STARTED ===" -ForegroundColor Green
Write-Host "  PID:    $($proc.Id)" -ForegroundColor Green
Write-Host "  Log:    $logPath" -ForegroundColor Green
Write-Host "  Status: https://ig-setter-pro.vercel.app/ (sidebar shows DAEMON ONLINE within 60-120s)" -ForegroundColor Green
Write-Host ""
Write-Host "Tail logs live:" -ForegroundColor Gray
Write-Host "  Get-Content $logPath -Wait -Tail 30" -ForegroundColor Gray
Write-Host ""
Write-Host "Stop daemon:" -ForegroundColor Gray
Write-Host "  Stop-Process -Id $($proc.Id) -Force" -ForegroundColor Gray
