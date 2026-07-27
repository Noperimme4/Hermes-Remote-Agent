# 🚀 Remote Agent - Easy Installation Guide

> **One-line install for server + client**  
> Supports: Ubuntu/Debian/CentOS/RHEL/Fedora/Arch/Alpine/Windows

---

## ⚡ Quick Install (Server)

```bash
curl -fsSL https://raw.githubusercontent.com/Noperimme4/remote-agent/main/install.sh | sudo bash
```

**Sample Output:**
```
[INFO] Installing Remote Agent Server...
[OK] Python 3.11 ready
[OK] User remote-agent ready
[OK] Code downloaded
[OK] Dependencies installed
[OK] Config written to /etc/remote-agent/server.env
[OK] Systemd service installed

═══════════════════════════════════════════
  TOKEN: a1b2c3d4e5f678901234567890abcdef1234567890abcdef1234567890abcdef
═══════════════════════════════════════════
  SAVE THIS TOKEN! You need it for client.

Next steps:
  1. Start service:  systemctl start remote-agent
  2. Check status:   systemctl status remote-agent
  3. View logs:      journalctl -u remote-agent -f

Client connection:
  export AGENT_TOKEN="a1b2c3d4e5f6..."
  python -m client.cli --host YOUR_SERVER_IP -i
```

---

## 💻 Client Install (Your Machine)

### Option 1: pipx (Recommended - Isolated)
```bash
pipx install git+https://github.com/Noperimme4/remote-agent.git
```

### Option 2: pip (Global)
```bash
pip install git+https://github.com/Noperimme4/remote-agent.git
```

### Option 3: Manual Clone
```bash
git clone https://github.com/Noperimme4/remote-agent.git
cd remote-agent
pip install -e .[client]
```

### Option 4: One-line Client Only
```bash
curl -fsSL https://raw.githubusercontent.com/Noperimme4/remote-agent/main/install.sh | bash -s -- --client
```

---

## 🔗 Connect & Use

### 1. Set Token Environment Variable
```bash
# Linux/macOS
export AGENT_TOKEN="your-token-from-server"

# PowerShell (Windows)
$env:AGENT_TOKEN = "your-token-from-server"

# CMD (Windows)
set AGENT_TOKEN=your-token-from-server
```

### 2. Interactive Shell (Full Terminal)
```bash
python -m client.cli --host YOUR_SERVER_IP -i
```

**Sample Session:**
```
╔══════════════════════════════════════════════════════════╗
║              🌐 Remote Agent Client v1.0                 ║
║         Secure remote command execution tool             ║
╚══════════════════════════════════════════════════════════╝

🔗 Connected to remote-agent-server
📍 Session: a1b2c3d4...
Type 'help' for commands, 'exit' to quit

🌐 /data/workspace $ ls -la
  ▶ ls -la
drwxr-xr-x 5 user user 4096 Jul 27 10:00 .
drwxr-xr-x 3 root root 4096 Jul 27 09:55 ..
-rw-r--r-- 1 user user  123 Jul 27 10:00 README.md
  ✓ Done (0.12s)
🌐 /data/workspace $
```

### 3. Single Command Execution
```bash
python -m client.cli --host YOUR_SERVER_IP -c "ls -la /data"
python -m client.cli --host YOUR_SERVER_IP -c "docker ps"
python -m client.cli --host YOUR_SERVER_IP -c "systemctl status nginx"
```

### 4. With TLS (Production)
```bash
python -m client.cli --host YOUR_SERVER_IP --tls --ca-cert ca.pem -i
```

---

## 📋 Server Management Commands

```bash
# Service status
systemctl status remote-agent

# Live logs
journalctl -u remote-agent -f

# Restart
sudo systemctl restart remote-agent

# View config
cat /etc/remote-agent/server.env

# Change token (then restart)
sudo nano /etc/remote-agent/server.env
sudo systemctl restart remote-agent
```

---

## 🔧 Advanced Configuration

### Config File: `/etc/remote-agent/server.env`

```ini
# Network
AGENT_HOST=0.0.0.0
AGENT_PORT=8765

# Authentication (REQUIRED)
AGENT_TOKEN=your-32-byte-hex-token

# Security - Allowed Commands
AGENT_ALLOWED_COMMANDS=ls,cat,git,docker,python3,pip,systemctl,journalctl,ssh,...
# Security - Blocked Commands
AGENT_BLOCKED_COMMANDS=reboot,shutdown,mkfs,dd,passwd,mount,umount,...
AGENT_ALLOW_SHELL=false        # true = allow bash -c
AGENT_ALLOW_FILES=true         # File operations enabled

# Logging
AGENT_LOG_LEVEL=INFO           # DEBUG, INFO, WARNING, ERROR
AGENT_LOG_FILE=/var/log/remote-agent/server.log

# Working Directory
AGENT_WORKDIR=/data/workspace

# TLS (Optional - for production)
# AGENT_TLS_CERT=/etc/remote-agent/cert.pem
# AGENT_TLS_KEY=/etc/remote-agent/key.pem
```

### Firewall (Restrict to Your IP Only)
```bash
# UFW
sudo ufw allow from YOUR_CLIENT_IP to any port 8765

# iptables
sudo iptables -A INPUT -p tcp -s YOUR_CLIENT_IP --dport 8765 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 8765 -j DROP
```

### TLS with Let's Encrypt (Production)
```bash
sudo certbot certonly --standalone -d agent.yourdomain.com
# Then in server.env:
AGENT_TLS_CERT=/etc/letsencrypt/live/agent.yourdomain.com/fullchain.pem
AGENT_TLS_KEY=/etc/letsencrypt/live/agent.yourdomain.com/privkey.pem
sudo systemctl restart remote-agent
```

---

## 🪟 Windows Server Install

```powershell
# PowerShell as Administrator
irm https://raw.githubusercontent.com/Noperimme4/remote-agent/main/scripts/install_windows.ps1 | iex
```

Or manual:
```powershell
git clone https://github.com/Noperimme4/remote-agent.git
cd remote-agent
.\scripts\install_windows.ps1
```

**Output:** Token displayed in console. Service `RemoteAgent` installed.

```powershell
Start-Service RemoteAgent
Get-Service RemoteAgent
Get-Content "C:\ProgramData\RemoteAgent\logs\service.log" -Wait
```

---

## 🐳 Docker (Optional)

```yaml
# docker-compose.yml
version: '3.8'
services:
  remote-agent:
    build: .
    ports:
      - "8765:8765"
    environment:
      - AGENT_TOKEN=${AGENT_TOKEN}
      - AGENT_HOST=0.0.0.0
      - AGENT_PORT=8765
      - AGENT_WORKDIR=/data/workspace
    volumes:
      - ./data/workspace:/data/workspace
      - ./config:/etc/remote-agent
      - ./logs:/var/log/remote-agent
    restart: unless-stopped
```

```bash
echo "AGENT_TOKEN=$(openssl rand -hex 32)" > .env
docker compose up -d
docker compose logs -f
```

---

## ❓ Quick Troubleshooting

| Issue | Fix |
|-------|-----|
| `Connection refused` | Service running? `systemctl status remote-agent` |
| `Authentication failed` | Token identical in client & server? No whitespace? |
| `Command not allowed` | Command in `AGENT_ALLOWED_COMMANDS`? |
| `Timeout` | Increase `AGENT_MAX_TIMEOUT` or use `--timeout` |
| `Module not found` | Run `pip install -e .[client]` |

---

## 📚 More Resources

- **Full Docs:** https://github.com/Noperimme4/remote-agent#readme
- **Report Bug:** https://github.com/Noperimme4/remote-agent/issues
- **Security:** Store token in `.env` or keyring, not shell history

---

<div align="center">
<strong>Built with ❤️ for developers</strong>
</div>