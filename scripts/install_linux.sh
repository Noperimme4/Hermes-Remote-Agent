#!/usr/bin/env bash
# Remote Agent Server - Linux Installation Script
# Supports: Ubuntu/Debian, CentOS/RHEL/Fedora, Arch, Alpine

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
REPO_URL="https://github.com/YOUR_USERNAME/remote-agent"
INSTALL_DIR="/opt/remote-agent"
SERVICE_USER="remote-agent"
CONFIG_DIR="/etc/remote-agent"
LOG_DIR="/var/log/remote-agent"
PYTHON_MIN_VERSION="3.10"

print_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $*"; }
print_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# ─── Detect OS ──────────────────────────────────────────────────

detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$ID
        VERSION=$VERSION_ID
    else
        print_error "Cannot detect OS"
        exit 1
    fi
    print_info "Detected OS: $PRETTY_NAME"
}

# ─── Check Requirements ─────────────────────────────────────────

check_python() {
    if command -v python3 &>/dev/null; then
        local version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"; then
            print_success "Python $version found"
            return 0
        else
            print_warning "Python $version found, but 3.10+ required"
        fi
    fi
    return 1
}

install_python() {
    print_info "Installing Python 3.10+..."
    case $OS in
        ubuntu|debian)
            apt-get update && apt-get install -y python3.11 python3.11-venv python3.11-dev
            update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
            ;;
        centos|rhel|fedora|rocky|almalinux)
            dnf install -y python3.11 python3.11-devel || yum install -y python3.11 python3.11-devel
            ;;
        arch|manjaro)
            pacman -S --noconfirm python
            ;;
        alpine)
            apk add python3 py3-pip
            ;;
        *)
            print_error "Unsupported OS for auto Python install: $OS"
            exit 1
            ;;
    esac
}

# ─── Create Service User ────────────────────────────────────────

create_user() {
    if id "$SERVICE_USER" &>/dev/null; then
        print_info "User $SERVICE_USER already exists"
    else
        useradd -r -s /bin/bash -d "$INSTALL_DIR" -m "$SERVICE_USER"
        print_success "Created user: $SERVICE_USER"
    fi
}

# ─── Install Application ────────────────────────────────────────

install_app() {
    print_info "Installing to $INSTALL_DIR..."
    
    # Create directories
    mkdir -p "$INSTALL_DIR"/{server,shared,scripts}
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$LOG_DIR"
    
    # Copy files (assuming we're running from repo root)
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    REPO_ROOT="$(dirname "$SCRIPT_DIR")"
    
    cp -r "$REPO_ROOT/server"/* "$INSTALL_DIR/server/"
    cp -r "$REPO_ROOT/shared"/* "$INSTALL_DIR/shared/"
    cp -r "$REPO_ROOT/scripts"/* "$INSTALL_DIR/scripts/" 2>/dev/null || true
    
    # Create virtual environment
    python3 -m venv "$INSTALL_DIR/venv"
    "$INSTALL_DIR/venv/bin/pip" install --upgrade pip
    "$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/server/requirements.txt" 2>/dev/null || true
    
    # Set permissions
    chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
    chown -R "$SERVICE_USER:$SERVICE_USER" "$LOG_DIR"
    chmod 750 "$CONFIG_DIR"
    
    print_success "Application installed"
}

# ─── Generate Config ────────────────────────────────────────────

generate_config() {
    local config_file="$CONFIG_DIR/server.env"
    
    if [[ -f "$config_file" ]]; then
        print_warning "Config already exists at $config_file"
        read -p "Overwrite? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Keeping existing config"
            return
        fi
    fi
    
    # Generate secure token
    local token=$(openssl rand -hex 32)
    
    cat > "$config_file" <<EOF
# Remote Agent Server Configuration
# Generated on $(date)

# Network
AGENT_HOST=0.0.0.0
AGENT_PORT=8765

# Authentication (REQUIRED - keep secret!)
AGENT_TOKEN=$token

# Security
AGENT_ALLOWED_COMMANDS=ls,cat,head,tail,grep,find,ps,top,htop,df,du,free,uptime,whoami,pwd,echo,date,python3,python,pip,npm,node,git,docker,kubectl,systemctl,journalctl,ss,netstat,lsof,curl,wget,tar,gzip,gunzip,zip,unzip,rsync,scp,ssh,mkdir,touch,cp,mv,rm,chmod,chown,ln,apt,apt-get,yum,dnf,pacman,pip3,pipx,vim,nano,code,less,more,bat,fd,rg,make,cmake,cargo,go,rustc,gcc,clang
AGENT_BLOCKED_COMMANDS=reboot,shutdown,halt,poweroff,init,mkfs,fdisk,parted,dd,wipefs,cryptsetup,passwd,userdel,groupdel,visudo,chroot,pivot_root,kexec,mount,umount
AGENT_MAX_TIMEOUT=300
AGENT_DEFAULT_TIMEOUT=60
AGENT_ALLOW_SHELL=false
AGENT_ALLOW_FILES=true

# Logging
AGENT_LOG_LEVEL=INFO
AGENT_LOG_FILE=$LOG_DIR/server.log

# Working directory
AGENT_WORKDIR=/data/workspace

# TLS (optional - generate with: openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes)
# AGENT_TLS_CERT=/etc/remote-agent/cert.pem
# AGENT_TLS_KEY=/etc/remote-agent/key.pem
EOF
    
    chmod 600 "$config_file"
    chown "$SERVICE_USER:$SERVICE_USER" "$config_file"
    
    print_success "Config generated at $config_file"
    print_warning "TOKEN: $token"
    print_warning "SAVE THIS TOKEN! You'll need it for client connections."
}

# ─── Install Systemd Service ────────────────────────────────────

install_systemd() {
    print_info "Installing systemd service..."
    
    cat > /etc/systemd/system/remote-agent.service <<EOF
[Unit]
Description=Remote Agent Server
After=network.target network-online.target
Wants=network-online.target
StartLimitIntervalSec=0

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
EnvironmentFile=$CONFIG_DIR/server.env
ExecStart=$INSTALL_DIR/venv/bin/python -m server.agent
Restart=always
RestartSec=5
StandardOutput=append:$LOG_DIR/server.log
StandardError=append:$LOG_DIR/server.log

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$INSTALL_DIR $LOG_DIR /data/workspace
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
RestrictNamespaces=true
LockPersonality=true
MemoryDenyWriteExecute=true
SystemCallFilter=@system-service
SystemCallErrorNumber=EPERM

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable remote-agent
    print_success "Systemd service installed and enabled"
}

# ─── Main ────────────────────────────────────────────────────────

main() {
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║     Remote Agent Server - Linux Installer               ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    
    # Check root
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi
    
    detect_os
    
    # Check/install Python
    if ! check_python; then
        install_python
        check_python || { print_error "Python installation failed"; exit 1; }
    fi
    
    create_user
    install_app
    generate_config
    install_systemd
    
    echo
    print_success "Installation complete!"
    echo
    echo "Next steps:"
    echo "  1. Review config: cat $CONFIG_DIR/server.env"
    echo "  2. Start service: systemctl start remote-agent"
    echo "  3. Check status:  systemctl status remote-agent"
    echo "  4. View logs:     journalctl -u remote-agent -f"
    echo
    echo "Client connection:"
    echo "  AGENT_TOKEN=<token> python -m client.cli --host <server-ip> -i"
}

main "$@"