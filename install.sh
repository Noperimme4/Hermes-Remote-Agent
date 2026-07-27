#!/usr/bin/env bash
# Remote Agent - One-line installer
# Usage: curl -fsSL https://raw.githubusercontent.com/Noperimme4/remote-agent/main/install.sh | bash
# Or:    curl -fsSL https://raw.githubusercontent.com/Noperimme4/remote-agent/main/install.sh | bash -s -- --client

set -euo pipefail

REPO="Noperimme4/remote-agent"
BRANCH="main"
INSTALL_DIR="/opt/remote-agent"
CONFIG_DIR="/etc/remote-agent"
LOG_DIR="/var/log/remote-agent"
SERVICE_USER="remote-agent"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${BLUE}[INFO]${NC} $*"; }
ok() { echo -e "${GREEN}[OK]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
err() { echo -e "${RED}[ERR]${NC} $*"; }

MODE="server"  # or "client"

# Parse args
for arg in "$@"; do
    case $arg in
        --client) MODE="client" ;;
        --server) MODE="server" ;;
        --help|-h)
            echo "Usage: $0 [--server|--client]"
            echo "  --server  Install server (default, requires root)"
            echo "  --client  Install client only (no root needed)"
            exit 0
            ;;
    esac
done

# ─── Server Install ────────────────────────────────────────────────
if [[ "$MODE" == "server" ]]; then
    [[ $EUID -eq 0 ]] || { err "Server install needs root: sudo bash $0"; exit 1; }

    log "Installing Remote Agent Server..."

    # Detect OS & install Python 3.10+
    . /etc/os-release
    log "Detected: $PRETTY_NAME"

    if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" 2>/dev/null; then
        log "Installing Python 3.11..."
        case $ID in
            ubuntu|debian) apt-get update && apt-get install -y python3.11 python3.11-venv ;;
            centos|rhel|fedora|rocky|almalinux) dnf install -y python3.11 python3.11-devel ;;
            arch|manjaro) pacman -S --noconfirm python ;;
            alpine) apk add python3 py3-pip ;;
            *) err "Unsupported OS: $ID"; exit 1 ;;
        esac
    fi

    # Create service user
    id "$SERVICE_USER" &>/dev/null || useradd -r -s /bin/bash -d "$INSTALL_DIR" -m "$SERVICE_USER"
    ok "User $SERVICE_USER ready"

    # Clone repo
    log "Downloading..."
    TMPDIR=$(mktemp -d)
    git clone -b "$BRANCH" --depth 1 "https://github.com/$REPO.git" "$TMPDIR" 2>/dev/null || {
        err "Git clone failed. Install git or check network."
        exit 1
    }

    # Install app
    log "Installing to $INSTALL_DIR..."
    mkdir -p "$INSTALL_DIR" "$CONFIG_DIR" "$LOG_DIR"
    cp -r "$TMPDIR/server" "$INSTALL_DIR/"
    cp -r "$TMPDIR/shared" "$INSTALL_DIR/"
    cp -r "$TMPDIR/scripts" "$INSTALL_DIR/" 2>/dev/null || true

    # Python venv
    python3 -m venv "$INSTALL_DIR/venv"
    "$INSTALL_DIR/venv/bin/pip" install --upgrade pip -q
    "$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/server/requirements.txt" -q

    # Permissions
    chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR" "$LOG_DIR"
    chmod 750 "$CONFIG_DIR"

    # Generate config
    TOKEN=$(openssl rand -hex 32)
    cat > "$CONFIG_DIR/server.env" <<EOF
# Remote Agent Server Configuration
# Generated: $(date)

AGENT_HOST=0.0.0.0
AGENT_PORT=8765
AGENT_TOKEN=$TOKEN
AGENT_ALLOWED_COMMANDS=ls,cat,head,tail,grep,find,ps,top,htop,df,du,free,uptime,whoami,pwd,date,python3,pip,git,docker,kubectl,systemctl,journalctl,ss,netstat,lsof,curl,wget,tar,gzip,gunzip,zip,unzip,rsync,scp,ssh,mkdir,touch,cp,mv,rm,chmod,chown,ln,apt,apt-get,yum,dnf,pacman,pip3,vim,nano,less,more,bat,fd,rg,make,cmake,cargo,go,rustc,gcc,clang
AGENT_BLOCKED_COMMANDS=reboot,shutdown,halt,poweroff,mkfs,fdisk,parted,dd,wipefs,cryptsetup,passwd,userdel,groupdel,visudo,chroot,mount,umount
AGENT_MAX_TIMEOUT=300
AGENT_DEFAULT_TIMEOUT=60
AGENT_ALLOW_SHELL=false
AGENT_ALLOW_FILES=true
AGENT_LOG_LEVEL=INFO
AGENT_LOG_FILE=$LOG_DIR/server.log
AGENT_WORKDIR=/data/workspace
EOF
    chmod 600 "$CONFIG_DIR/server.env"
    chown "$SERVICE_USER:$SERVICE_USER" "$CONFIG_DIR/server.env"

    # Systemd service
    cat > /etc/systemd/system/remote-agent.service <<EOF
[Unit]
Description=Remote Agent Server
After=network.target network-online.target
Wants=network-online.target

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

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable remote-agent

    # Cleanup
    rm -rf "$TMPDIR"

    echo
    ok "Installation complete!"
    echo
    echo "═══════════════════════════════════════════"
    echo "  TOKEN: $TOKEN"
    echo "═══════════════════════════════════════════"
    echo "  SAVE THIS TOKEN! You need it for client."
    echo
    echo "Next steps:"
    echo "  1. Start service:  systemctl start remote-agent"
    echo "  2. Check status:   systemctl status remote-agent"
    echo "  3. View logs:      journalctl -u remote-agent -f"
    echo
    echo "Client connection:"
    echo "  export AGENT_TOKEN=\"$TOKEN\""
    echo "  python -m client.cli --host YOUR_SERVER_IP -i"
    exit 0
fi

# ─── Client Install ────────────────────────────────────────────────
if [[ "$MODE" == "client" ]]; then
    log "Installing Remote Agent Client..."

    # Check Python
    if ! command -v python3 &>/dev/null; then
        err "Python 3 not found. Install Python 3.10+ first."
        exit 1
    fi

    python3 -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" 2>/dev/null || {
        err "Python 3.10+ required. Current: $(python3 --version)"
        exit 1
    }

    # Install in user site or venv
    if [[ -n "${VIRTUAL_ENV:-}" ]]; then
        PIP="pip"
    else
        PIP="pip install --user"
    fi

    $PIP install --upgrade pip -q
    $PIP install git+https://github.com/$REPO.git@$BRANCH#subdirectory=client -q

    ok "Client installed!"
    echo
    echo "Usage:"
    echo "  export AGENT_TOKEN=\"your-token-from-server\""
    echo "  python -m client.cli --host SERVER_IP -i          # Interactive shell"
    echo "  python -m client.cli --host SERVER_IP -c \"ls -la\" # Single command"
    echo
    echo "Full docs: https://github.com/Noperimme4/remote-agent#readme"
    exit 0
fi