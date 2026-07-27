<#>
.SYNOPSIS
    Remote Agent Server - Windows Installation Script
.DESCRIPTION
    Installs Remote Agent as a Windows Service using NSSM (Non-Sucking Service Manager)
    Supports Windows 10/11, Windows Server 2019/2022
#>

param(
    [string]$InstallDir = "C:\Program Files\RemoteAgent",
    [string]$ConfigDir = "C:\ProgramData\RemoteAgent",
    [string]$LogDir = "C:\ProgramData\RemoteAgent\logs",
    [switch]$NoService,
    [switch]$Uninstall
)

# ─── Colors ──────────────────────────────────────────────────────

function Write-Info { Write-Host "[INFO] $($args[0])" -ForegroundColor Cyan }
function Write-Success { Write-Host "[SUCCESS] $($args[0])" -ForegroundColor Green }
function Write-Warning { Write-Host "[WARNING] $($args[0])" -ForegroundColor Yellow }
function Write-Error { Write-Host "[ERROR] $($args[0])" -ForegroundColor Red }

# ─── Check Admin ─────────────────────────────────────────────────

if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "This script must be run as Administrator"
    exit 1
}

# ─── Uninstall ───────────────────────────────────────────────────

if ($Uninstall) {
    Write-Info "Uninstalling Remote Agent..."
    
    # Stop and remove service
    if (Get-Service "RemoteAgent" -ErrorAction SilentlyContinue) {
        Stop-Service "RemoteAgent" -Force -ErrorAction SilentlyContinue
        sc.exe delete "RemoteAgent" | Out-Null
        Write-Success "Service removed"
    }
    
    # Remove files
    if (Test-Path $InstallDir) {
        Remove-Item $InstallDir -Recurse -Force
        Write-Success "Removed $InstallDir"
    }
    
    if (Test-Path $ConfigDir) {
        Remove-Item $ConfigDir -Recurse -Force
        Write-Success "Removed $ConfigDir"
    }
    
    # Remove NSSM if we installed it
    if (Test-Path "$env:SystemRoot\nssm.exe") {
        Remove-Item "$env:SystemRoot\nssm.exe" -Force -ErrorAction SilentlyContinue
    }
    
    Write-Success "Uninstall complete"
    exit 0
}

# ─── Check Python ────────────────────────────────────────────────

function Check-Python {
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $version = python --version 2>&1
        if ($version -match 'Python (\d+)\.(\d+)') {
            $major = [int]$matches[1]
            $minor = [int]$matches[2]
            if ($major -ge 3 -and $minor -ge 10) {
                Write-Success "Found $version"
                return $true
            }
        }
    }
    Write-Warning "Python 3.10+ not found"
    return $false
}

function Install-Python {
    Write-Info "Installing Python 3.11 via winget..."
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        winget install --id Python.Python.3.11 --silent --accept-source-agreements --accept-package-agreements
        $env:PATH = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
        refreshenv 2>$null
        return (Check-Python)
    } else {
        Write-Error "winget not available. Please install Python 3.10+ manually from python.org"
        return $false
    }
}

# ─── Download NSSM ───────────────────────────────────────────────

function Get-NSSM {
    $nssmPath = "$env:SystemRoot\nssm.exe"
    if (Test-Path $nssmPath) { return $nssmPath }
    
    Write-Info "Downloading NSSM..."
    $url = "https://github.com/nssm/nssm/releases/download/v2.24/nssm-2.24.zip"
    $tempZip = "$env:TEMP\nssm.zip"
    $tempDir = "$env:TEMP\nssm"
    
    try {
        Invoke-WebRequest -Uri $url -OutFile $tempZip -UseBasicParsing
        Expand-Archive -Path $tempZip -DestinationPath $tempDir -Force
        $arch = if ([Environment]::Is64BitOperatingSystem) { "win64" } else { "win32" }
        Copy-Item "$tempDir\nssm-2.24\$arch\nssm.exe" -Destination $nssmPath -Force
        Write-Success "NSSM installed to $nssmPath"
        return $nssmPath
    } catch {
        Write-Error "Failed to download NSSM: $_"
        return $null
    } finally {
        Remove-Item $tempZip -ErrorAction SilentlyContinue
        Remove-Item $tempDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}

# ─── Generate Token ──────────────────────────────────────────────

function Generate-Token {
    $bytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    return [System.BitConverter]::ToString($bytes).Replace('-', '').ToLower()
}

# ─── Create Directories ──────────────────────────────────────────

function Create-Directories {
    foreach ($dir in $InstallDir, $ConfigDir, $LogDir, "$InstallDir\server", "$InstallDir\shared", "$InstallDir\scripts") {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
            Write-Info "Created: $dir"
        }
    }
}

# ─── Copy Files ──────────────────────────────────────────────────

function Copy-Files {
    $scriptDir = Split-Path $MyInvocation.MyCommand.Path -Parent
    $repoRoot = Split-Path $scriptDir -Parent
    
    Write-Info "Copying application files..."
    Copy-Item "$repoRoot\server\*" -Destination "$InstallDir\server\" -Recurse -Force
    Copy-Item "$repoRoot\shared\*" -Destination "$InstallDir\shared\" -Recurse -Force
    Copy-Item "$repoRoot\scripts\*" -Destination "$InstallDir\scripts\" -Recurse -Force -ErrorAction SilentlyContinue
    
    # Create virtual environment
    Write-Info "Creating Python virtual environment..."
    python -m venv "$InstallDir\venv"
    & "$InstallDir\venv\Scripts\pip.exe" install --upgrade pip -q
    if (Test-Path "$InstallDir\server\requirements.txt") {
        & "$InstallDir\venv\Scripts\pip.exe" install -r "$InstallDir\server\requirements.txt" -q
    }
    Write-Success "Virtual environment ready"
}

# ─── Generate Config ─────────────────────────────────────────────

function Generate-Config {
    $configFile = "$ConfigDir\server.env"
    
    if (Test-Path $configFile -and -not $Force) {
        Write-Warning "Config already exists at $configFile"
        $choice = Read-Host "Overwrite? (y/N)"
        if ($choice -notmatch '^[yY]$') {
            Write-Info "Keeping existing config"
            return
        }
    }
    
    $token = Generate-Token
    $workDir = if (Test-Path "C:\data\workspace") { "C:\data\workspace" } else { "$env:USERPROFILE\remote-agent-workspace" }
    if (-not (Test-Path $workDir)) { New-Item -ItemType Directory -Path $workDir -Force | Out-Null }
    
    $config = @"
# Remote Agent Server Configuration
# Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')

# Network
AGENT_HOST=0.0.0.0
AGENT_PORT=8765

# Authentication (REQUIRED - keep secret!)
AGENT_TOKEN=$token

# Security - Allowed commands (comma-separated)
AGENT_ALLOWED_COMMANDS=dir,type,findstr,where,get-childitem,get-content,select-string,get-process,get-service,get-item,get-childitem,python,python3,pip,npm,node,git,docker,kubectl,powershell,cmd,netstat,ipconfig,systeminfo,whoami,hostname,date,time,echo,mkdir,copy-item,move-item,remove-item,new-item,set-location,get-location,compress-archive,expand-archive,tar,curl,invoke-webrequest,winget,choco,scoop,make,cmake,cargo,go,rustc,dotnet,msbuild

# Security - Blocked commands
AGENT_BLOCKED_COMMANDS=shutdown,restart-computer,stop-computer,format,clear-disk,initialize-disk,new-partition,remove-partition,set-partition,reset-computermachinepassword,remove-localuser,remove-localgroup,disable-localuser,enable-localuser,set-localuser,set-localgroup

AGENT_MAX_TIMEOUT=300
AGENT_DEFAULT_TIMEOUT=60
AGENT_ALLOW_SHELL=false
AGENT_ALLOW_FILES=true

# Logging
AGENT_LOG_LEVEL=INFO
AGENT_LOG_FILE=$LogDir\server.log

# Working directory
AGENT_WORKDIR=$workDir

# TLS (optional)
# AGENT_TLS_CERT=C:\ProgramData\RemoteAgent\cert.pem
# AGENT_TLS_KEY=C:\ProgramData\RemoteAgent\key.pem
"@
    
    Set-Content -Path $configFile -Value $config -Encoding UTF8
    # Restrict permissions to Administrators and SYSTEM
    $acl = Get-Acl $configFile
    $acl.SetAccessRuleProtection($true, $false)
    $rule = New-Object System.Security.AccessControl.FileSystemAccessRule("Administrators", "FullControl", "Allow")
    $acl.AddAccessRule($rule)
    $rule = New-Object System.Security.AccessControl.FileSystemAccessRule("SYSTEM", "FullControl", "Allow")
    $acl.AddAccessRule($rule)
    Set-Acl $configFile $acl
    
    Write-Success "Config generated at $configFile"
    Write-Warning "=========================================="
    Write-Warning "TOKEN: $token"
    Write-Warning "SAVE THIS TOKEN! Required for client connections."
    Write-Warning "=========================================="
    
    return $token
}

# ─── Install Service ─────────────────────────────────────────────

function Install-Service {
    if ($NoService) {
        Write-Info "Skipping service installation (--NoService flag)"
        return
    }
    
    $nssm = Get-NSSM
    if (-not $nssm) { return }
    
    Write-Info "Installing Windows Service..."
    
    $pythonExe = "$InstallDir\venv\Scripts\python.exe"
    $scriptPath = "$InstallDir\server\agent.py"
    
    & $nssm install "RemoteAgent" $pythonExe "-m server.agent" 2>$null
    & $nssm set "RemoteAgent" AppDirectory $InstallDir 2>$null
    & $nssm set "RemoteAgent" AppStdout "$LogDir\service.log" 2>$null
    & $nssm set "RemoteAgent" AppStderr "$LogDir\service-error.log" 2>$null
    & $nssm set "RemoteAgent" AppEnvironmentExtra "AGENT_CONFIG_DIR=$ConfigDir" 2>$null
    & $nssm set "RemoteAgent" Start "SERVICE_AUTO_START" 2>$null
    & $nssm set "RemoteAgent" Description "Remote Agent Server - Cross-platform remote command execution" 2>$null
    
    # Set recovery actions
    & $nssm set "RemoteAgent" ActionOnExit 1 2>$null  # Restart on exit
    & $nssm set "RemoteAgent" AppRestartDelay 5000 2>$null
    
    Write-Success "Service 'RemoteAgent' installed"
    Write-Info "Start with: Start-Service RemoteAgent"
    Write-Info "View logs:  Get-Content $LogDir\service.log -Wait"
}

# ─── Main ────────────────────────────────────────────────────────

Write-Host "╔══════════════════════════════════════════════════════════╗"
Write-Host "║     Remote Agent Server - Windows Installer             ║"
Write-Host "╚══════════════════════════════════════════════════════════╝"

# Check Python
if (-not (Check-Python)) {
    if (-not (Install-Python)) {
        Write-Error "Python 3.10+ is required. Install manually from python.org"
        exit 1
    }
}

Create-Directories
Copy-Files
$token = Generate-Config

if (-not $NoService) {
    Install-Service
}

Write-Host ""
Write-Success "Installation complete!"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Review config: notepad $ConfigDir\server.env"
Write-Host "  2. Start service: Start-Service RemoteAgent"
Write-Host "  3. Check status:  Get-Service RemoteAgent"
Write-Host "  4. View logs:     Get-Content $LogDir\service.log -Wait"
Write-Host ""
Write-Host "Client connection:"
Write-Host "  `$env:AGENT_TOKEN='$token' python -m client.cli --host <server-ip> -i"