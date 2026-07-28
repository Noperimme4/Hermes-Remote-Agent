#!/usr/bin/env bash
# Remote Agent - One-line Installer
# Usage: curl -fsSL https://raw.githubusercontent.com/Noperimme4/remote-agent/main/scripts/install.sh | sudo bash

set -euo pipefail

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
ok() { echo -e "${GREEN}[✓]${NC} $*"; }
info() { echo -e "${BLUE}[i]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err() { echo -e "${RED}[✗]${NC} $*" >&2; }

# Must be root
[[ $EUID -eq 0 ]] || { err "Run as root: sudo bash $0"; exit 1; }

# Config
REPO="Noperimme4/remote-agent"
BRANCH="master"
INSTALL_DIR="/opt/remote-agent"
CONFIG_DIR="/etc/remote-agent"
LOG_DIR="/var/log/remote-agent"
SERVICE_USER="remote-agent"
WORK_DIR="/data/workspace"

# Generate secure token
TOKEN=$(openssl rand -hex 32)
TMPDIR=$(mktemp -d)

info "Installing Remote Agent..."

# Detect OS & install Python 3.10+
if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" 2>/dev/null; then
    info "Installing Python 3.11..."
    if command -v apt-get &>/dev/null; then
        apt-get update -qq && apt-get install -y -qq python3.11 python3.11-venv python3.11-dev >/dev/null
        update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
    elif command -v dnf &>/dev/null; then
        dnf install -y -q python3.11 python3.11-devel >/dev/null
    elif command -v pacman &>/dev/null; then
        pacman -S --noconfirm python >/dev/null
    elif command -v apk &>/dev/null; then
        apk add python3 py3-pip >/dev/null
    else
        err "Unsupported OS. Install Python 3.10+ manually."
        exit 1
    fi
fi
ok "Python $(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")') ready"

# Create service user
id "$SERVICE_USER" &>/dev/null || useradd -r -s /bin/bash -d "$INSTALL_DIR" -m "$SERVICE_USER"
ok "User $SERVICE_USER ready"

# Clone repo
info "Downloading..."
git clone -q --depth 1 --branch "$BRANCH" "https://github.com/$REPO.git" "$TMPDIR/repo" 2>/dev/null || {
    err "Git clone failed. Check internet access."
    exit 1
}
ok "Code downloaded"

# Install app
mkdir -p "$INSTALL_DIR" "$CONFIG_DIR" "$LOG_DIR" "$WORK_DIR"
rsync -a "$TMPDIR/repo/server/" "$INSTALL_DIR/server/"
rsync -a "$TMPDIR/repo/shared/" "$INSTALL_DIR/shared/"
rsync -a "$TMPDIR/repo/scripts/" "$INSTALL_DIR/scripts/" 2>/dev/null || true
chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR" "$LOG_DIR" "$WORK_DIR"

# Python venv
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install -q --upgrade pip
"$INSTALL_DIR/venv/bin/pip" install -q -r "$INSTALL_DIR/server/requirements.txt" 2>/dev/null || true
ok "Dependencies installed"

# Config
cat > "$CONFIG_DIR/server.env" <<EOF
AGENT_HOST=0.0.0.0
AGENT_PORT=8765
AGENT_TOKEN=$TOKEN
AGENT_LOG_LEVEL=INFO
AGENT_LOG_FILE=$LOG_DIR/server.log
AGENT_WORKDIR=$WORK_DIR
AGENT_ALLOW_SHELL=false
AGENT_ALLOW_FILES=true
AGENT_REMOTE_MOUNTS=/:/,/home:/home,/data:/data,/tmp:/tmp
EOF
chmod 600 "$CONFIG_DIR/server.env"
chown "$SERVICE_USER:$SERVICE_USER" "$CONFIG_DIR/server.env"
ok "Config written to $CONFIG_DIR/server.env"

# Systemd service
cat > /etc/systemd/system/remote-agent.service <<EOF
[Unit]
Description=Remote Agent Server
After=network-online.target
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
ReadWritePaths=$INSTALL_DIR $LOG_DIR $WORK_DIR

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable remote-agent >/dev/null
ok "Systemd service installed"

# Start service
systemctl start remote-agent
sleep 2

# Verify
if systemctl is-active --quiet remote-agent; then
    ok "Service started successfully!"
    IP=$(hostname -I | awk '{print $1}')
    echo
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${GREEN}🔑 YOUR TOKEN (SAVE THIS!)${NC}"
    echo "   $TOKEN"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo
    echo "Server IP: $IP"
    echo "Port: 8765"
    echo
    echo "Commands:"
    echo "  Status:  systemctl status remote-agent"
    echo "  Logs:    journalctl -u remote-agent -f"
    echo "  Config:  cat $CONFIG_DIR/server.env"
    echo
    echo "Client usage:"
    echo "  export AGENT_TOKEN=\"$TOKEN\""
    echo "  python -m client.cli --host $IP -i"
else
    err "Service failed to start"
    journalctl -u remote-agent --no-pager -n 20
    exit 1
fi

# Cleanup
rm -rf "$TMPDIR"