# Odoo Agent Runtime - Windows installer
param(
    [string]$InstallDir = "$env:USERPROFILE\odoo-agent-runtime"
)

$ErrorActionPreference = "Stop"
function Log($Message) { Write-Host "[✓] $Message" -ForegroundColor Green }
function Warn($Message) { Write-Host "[!] $Message" -ForegroundColor Yellow }
function Err($Message) { Write-Host "[✗] $Message" -ForegroundColor Red }
function Ask($Prompt, $Default = "") {
    if ($Default) { $value = Read-Host "$Prompt [$Default]"; if ($value) { return $value }; return $Default }
    return Read-Host $Prompt
}
function AskYesNo($Prompt, $Default = "no") {
    $value = Read-Host "$Prompt [$Default]"
    if (-not $value) { $value = $Default }
    return $value.ToLower() -in @("y", "yes")
}

Write-Host ""
Write-Host "Odoo Agent Runtime Installer (Windows)"
Write-Host ""

$python = $null
foreach ($cmd in @("python", "py")) {
    try {
        if ($cmd -eq "py") { $version = & $cmd -3 --version 2>&1 } else { $version = & $cmd --version 2>&1 }
        if ($version -match "Python (\d+)\.(\d+)" -and ([int]$Matches[1] -gt 3 -or ([int]$Matches[1] -eq 3 -and [int]$Matches[2] -ge 8))) {
            $python = $cmd
            break
        }
    } catch {}
}
if (-not $python) {
    Err "Python 3.8+ not found. Install Python first: https://www.python.org/downloads/"
    exit 1
}
Log "Python found"

$OdooUrl = Ask "Odoo URL" "http://localhost:8069"
$ApiKey = Ask "Runtime API key"
while ([string]::IsNullOrWhiteSpace($ApiKey)) {
    Err "Runtime API key cannot be empty."
    $ApiKey = Ask "Runtime API key"
}
$RuntimeName = Ask "Runtime name" $env:COMPUTERNAME
$PollInterval = Ask "Poll interval in seconds" "10"
$InstallMode = Ask "Install mode: scheduled-task or manual" "manual"

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (Test-Path "$scriptDir\daemon.py") {
    Copy-Item "$scriptDir\daemon.py" "$InstallDir\daemon.py" -Force
    if (Test-Path "$scriptDir\requirements.txt") { Copy-Item "$scriptDir\requirements.txt" "$InstallDir\requirements.txt" -Force }
    Log "Files copied from local source"
} else {
    $baseUrl = "https://raw.githubusercontent.com/nicolasramos-es/odoo-agent-runtime/main"
    Invoke-WebRequest -Uri "$baseUrl/daemon.py" -OutFile "$InstallDir\daemon.py"
    Invoke-WebRequest -Uri "$baseUrl/requirements.txt" -OutFile "$InstallDir\requirements.txt"
    Log "Files downloaded"
}

if ($python -eq "py") { & $python -3 -m pip install -q -r "$InstallDir\requirements.txt" } else { & $python -m pip install -q -r "$InstallDir\requirements.txt" }
Log "Dependencies installed"

$envFile = Join-Path $InstallDir ".env"
if ((Test-Path $envFile) -and -not (AskYesNo "Existing .env found. Overwrite it?" "no")) {
    $envFile = Join-Path $InstallDir ".env.new"
    Warn "Keeping existing .env. Writing new configuration to .env.new."
}

@"
# Odoo Agent Runtime Configuration
ODOO_URL=$OdooUrl
API_KEY=$ApiKey
RUNTIME_NAME=$RuntimeName
POLL_INTERVAL=$PollInterval
"@ | Out-File -FilePath $envFile -Encoding ASCII
Log "$(Split-Path -Leaf $envFile) written"
if ((Split-Path -Leaf $envFile) -ne ".env") {
    Warn "Scheduled Task creation skipped because the active .env was not overwritten."
    $InstallMode = "manual"
}

if ($InstallMode.ToLower() -eq "scheduled-task") {
    $confirm = Ask "Create and start a Windows Scheduled Task? yes or no" "no"
    if ($confirm.ToLower() -eq "yes") {
        $taskName = "OdooAgentRuntime"
        $pythonExe = if ($python -eq "py") { "py" } else { (Get-Command $python).Source }
        $pythonArgs = if ($python -eq "py") { "-3 `"$InstallDir\daemon.py`"" } else { "`"$InstallDir\daemon.py`"" }
        $action = New-ScheduledTaskAction -Execute $pythonExe -Argument $pythonArgs -WorkingDirectory $InstallDir
        $trigger = New-ScheduledTaskTrigger -AtLogOn
        $principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -RunLevel Limited
        Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Force | Out-Null
        Start-ScheduledTask -TaskName $taskName
        Log "Scheduled Task created and started"
    } else {
        Warn "Scheduled Task skipped. Use manual mode."
    }
} else {
    Warn "Manual mode selected. No Scheduled Task was created."
}

Write-Host ""
Log "Installation complete"
Write-Host "Config: $InstallDir\.env"
Write-Host "Manual run: $python $InstallDir\daemon.py"
