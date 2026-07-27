# 🌐 Remote Agent

> **ابزار اجرای دستور امن از راه دور** — سرور روی VPS/سرور، کلاینت روی سیستم شما. بدون VPN، بدون پورت باز اضافی، با احراز هویت توکن.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20Windows%20%7C%20macOS-lightgrey.svg)](https://github.com/Noperimme4/remote-agent)

---

## ✨ ویژگی‌ها

| ویژگی | توضیح |
|----------|----------|
| 🔐 **احراز هویت توکنی** | توکن ۲۵۶‌بیت تصادفی، ارسال در هدر، بدون رمز در کانفیگ |
| 🛡 **لیست سفید/سیاه دستورات** | فقط دستورات مجاز اجرا می‌شوند، دستورات خطرناک مسدود |
| 📡 **استریم زنده خروجی** | دیدن `stdout`/`stderr` لحظه‌به‌لحظه در حالت تعاملی |
| 🐚 **PTY Shell** | ترمینال کامل با پشتیبانی `vim`، `htop`، `ssh`، `sudo`، `docker exec -it` |
| 📁 **مدیریت فایل** | مرور، آپلود، دانلود، مشاهده، حذف، ساخت پوشه |
| 🤖 **Hermes AI** | چت با Hermes AI روی سرور ریموت |
| 🐳 **Docker Manager** | کانتینرها، ایمیج‌ها، لاگ‌ها، استات‌ها |
| ⚙️ **Services** | systemctl start/stop/restart/status/enable/disable |
| 📊 **System Monitor** | CPU، RAM، Disk، Processes، Load |
| 📝 **Logs** | journalctl، dmesg، auth logs |
| ❤️ **Heartbeat** | تشخیص قطع اتصال، تمیز کردن سشن‌های مرده |
| 🔒 **TLS/SSL** | رمزگذاری ترافیک با گواهی self-signed یا CA |
| 🐳 **Docker Ready** | ایمیج رسمی، docker-compose برای استقرار سریع |
| ⚡ **Async/Non-blocking** | مبتنی بر `asyncio`، مدیریت صدها اتصال همزمان |

---

## 📋 فهرست مطالب

- [⚡ نصب سریع (یک خط)](#-نصب-سریع-یک-خط)
- [📦 نصب کامل (پیشرفته / پروداکشن)](#-نصب-کامل-پیشرفته--پروداکشن)
- [🐳 نصب با Docker](#-نصب-با-docker)
- [🪟 نصب روی Windows](#-نصب-روی-windows)
- [🔑 اتصال و استفاده](#-اتصال-و-استفاده)
- [🎯 منوی تعاملی](#-منوی-تعاملی)
- [⌨️ تمام دستورات CLI](#️-تمام-دستورات-cli)
- [👤 مدیریت پروفایل‌ها](#-مدیریت-پروفایل‌ها)
- [⚙️ تنظیمات سرور](#️-تنظیمات-سرور)
- [🔐 امنیت](#-امنیت)
- [🐛 عیب‌یابی](#-عیب‌یابی)

---

## ⚡ نصب سریع (یک خط)

> **برای کاربران با تجربه** — فقط کپی کنید، پیست کنید، اینتر بزنید.

### سرور (Linux)

```bash
curl -fsSL https://raw.githubusercontent.com/Noperimme4/remote-agent/main/scripts/install.sh | sudo bash
```

**خروجی:**
```bash
[✓] Python 3.11 ready
[✓] User remote-agent created
[✓] Code downloaded
[✓] Dependencies installed
[✓] Config written to /etc/remote-agent/server.env
[✓] Systemd service installed

═══════════════════════════════════════════
  🔑 YOUR TOKEN (SAVE THIS!)
  a1b2c3d4e5f678901234567890abcdef1234567890abcdef1234567890abcdef
═══════════════════════════════════════════

Next steps:
  1. Start service:  systemctl start remote-agent
  2. Check status:   systemctl status remote-agent
  3. View logs:      journalctl -u remote-agent -f

Client usage:
  export AGENT_TOKEN="a1b2c3d4e5f6..."
  python -m client.cli --host YOUR_SERVER_IP -i
```

```bash
# سرویس را شروع و فعال کنید
sudo systemctl start remote-agent
sudo systemctl enable remote-agent
```

### کلاینت (همه پلتفرم‌ها)

```bash
# 🐧 Linux / macOS
pipx install git+https://github.com/Noperimme4/remote-agent.git
# یا
pip install git+https://github.com/Noperimme4/remote-agent.git

# 🪟 Windows (PowerShell)
pipx install git+https://github.com/Noperimme4/remote-agent.git
# یا
pip install git+https://github.com/Noperimme4/remote-agent.git
```

```bash
# تست سریع
export AGENT_TOKEN="your-token-from-server"
agent --host YOUR_SERVER_IP -c "echo 'Connected!'"
```

---

## 📦 نصب کامل (پیشرفته / پروداکشن)

> **تنها راهنمای نصب کامل برای محیط پروداکشن، امنیت بالا، و کنترل کامل** — هاردنینگ، TLS، فایروال محدود، Fail2Ban، Logrotate، مانیتورینگ، چک‌لیست Go-Live.

### 📋 پیش‌نیازهای پروداکشن

| مورد | حداقل | توصیه شده | چک |
|------|--------|-----------|-----|
| **OS** | Ubuntu 20.04+, Debian 11+, RHEL 8+ | Ubuntu 22.04 LTS / Debian 12 | ☐ |
| **Python** | 3.10 | 3.11 یا 3.12 | ☐ |
| **RAM** | 512 MB | 1 GB+ | ☐ |
| **Disk** | 1 GB | 5 GB+ (لاگ‌ها/داده‌ها) | ☐ |
| **Network** | IPv4 | IPv4 + IPv6، فایروال کانفیگ | ☐ |
| **Access** | sudo/root | یوزر غیر روت با sudo محدود | ☐ |

**بررسی سریع سرور:**
```bash
lsb_release -a          # توزیع
python3 --version       # 3.10+
free -h                 # رم
df -h /                 # دیسک
ip a | grep inet        # IPها
sudo -n true 2>&1 && echo "sudo OK" || echo "sudo needed"
```

---

### ۱. هاردنینگ پایه سرور

```bash
# آپدیت و ابزارها
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git ca-certificates gnupg lsb-release \
    python3 python3-venv python3-dev build-essential \
    ufw fail2ban htop net-tools logrotate

# فایروال (فقط SSH + Agent)
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 8765/tcp comment 'Remote Agent'
sudo ufw --force enable
sudo ufw status verbose

# SSH سخت‌سازی
sudo sed -i 's/^#PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sudo sed -i 's/^#PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl reload sshd

# Timezone
sudo timedatectl set-timezone Asia/Tehran
```

---

### ۲. نصب دستی سرور (کنترل کامل)

#### ۲.۱ یوزر و دایرکتوری‌ها
```bash
sudo useradd -r -s /bin/bash -d /opt/remote-agent -m remote-agent

sudo mkdir -p /opt/remote-agent/{server,shared,scripts,venv}
sudo mkdir -p /etc/remote-agent
sudo mkdir -p /var/log/remote-agent
sudo mkdir -p /data/workspace

sudo chown -R remote-agent:remote-agent /opt/remote-agent /var/log/remote-agent /data/workspace
sudo chmod 750 /etc/remote-agent
sudo chmod 755 /data/workspace
```

#### ۲.۲ کد و محیط مجازی
```bash
cd /opt/remote-agent
rsync -a /path/to/cloned/remote-agent/server/ /opt/remote-agent/server/
rsync -a /path/to/cloned/remote-agent/shared/ /opt/remote-agent/shared/
rsync -a /path/to/cloned/remote-agent/scripts/ /opt/remote-agent/scripts/
sudo chown -R remote-agent:remote-agent /opt/remote-agent

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r server/requirements.txt
python -c "from server.agent import RemoteAgentServer; print('✓ Import OK')"
deactivate
```

#### ۲.۳ توکن و کانفیگ امن
```bash
TOKEN=$(openssl rand -hex 32)
echo "TOKEN=$TOKEN"

sudo tee /etc/remote-agent/server.env > /dev/null <<EOF
# Network
AGENT_HOST=0.0.0.0
AGENT_PORT=8765

# Auth (REQUIRED)
AGENT_TOKEN=$TOKEN

# Security - Allowed (comma-separated, no spaces)
AGENT_ALLOWED_COMMANDS=ls,cat,head,tail,grep,find,ps,top,htop,df,du,free,uptime,whoami,pwd,date,python3,pip,git,docker,kubectl,systemctl,journalctl,ssh,scp,rsync,tar,zip,unzip,mkdir,cp,mv,rm,chmod,chown,ln,apt,apt-get,yum,dnf,pacman,pip3,npm,make,cmake,cargo,go,rustc,gcc,clang,vim,nano,less,more,bat,fd,rg,curl,wget,ping,dig,host,nslookup,ip,ss,netstat,lsof,stat,file,diff,patch,tee,awk,sed,cut,sort,uniq,wc,tr,xargs

# Security - Blocked (never allowed)
AGENT_BLOCKED_COMMANDS=reboot,shutdown,halt,poweroff,mkfs,fdisk,parted,dd,wipefs,cryptsetup,passwd,userdel,groupdel,visudo,chroot,pivot_root,kexec,mount,umount,su,sudo,doas,runuser

# Limits
AGENT_MAX_TIMEOUT=300
AGENT_DEFAULT_TIMEOUT=60
AGENT_ALLOW_SHELL=false
AGENT_ALLOW_FILES=true

# Logging
AGENT_LOG_LEVEL=INFO
AGENT_LOG_FILE=/var/log/remote-agent/server.log

# Working Directory
AGENT_WORKDIR=/data/workspace

# TLS (uncomment for production)
# AGENT_TLS_CERT=/etc/remote-agent/certs/cert.pem
# AGENT_TLS_KEY=/etc/remote-agent/certs/key.pem
EOF

sudo chmod 600 /etc/remote-agent/server.env
sudo chown remote-agent:remote-agent /etc/remote-agent/server.env
cat /etc/remote-agent/server.env
```

---

### ۳. سرویس systemd هاردند شده

```bash
sudo tee /etc/systemd/system/remote-agent.service > /dev/null <<'EOF'
[Unit]
Description=Remote Agent Server
Documentation=https://github.com/Noperimme4/remote-agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=remote-agent
Group=remote-agent
WorkingDirectory=/opt/remote-agent
EnvironmentFile=/etc/remote-agent/server.env
ExecStart=/opt/remote-agent/venv/bin/python -m server.agent
ExecReload=/bin/kill -HUP $MAINPID

Restart=always
RestartSec=5
StartLimitIntervalSec=60
StartLimitBurst=3

LimitNOFILE=65536
LimitNPROC=4096
MemoryLimit=512M
CPUQuota=200%

StandardOutput=append:/var/log/remote-agent/server.log
StandardError=append:/var/log/remote-agent/server.log
SyslogIdentifier=remote-agent

# Security Hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictNamespaces=true
RestrictRealtime=true
RestrictSUIDSGID=true
RemoveIPC=true
PrivateDevices=true
ProtectProc=invisible
ProcSubset=pid
LockPersonality=true
MemoryDenyWriteExecute=true
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
SystemCallFilter=@system-service
SystemCallErrorNumber=EPERM

ReadWritePaths=/opt/remote-agent /var/log/remote-agent /data/workspace /etc/remote-agent
ReadOnlyPaths=/usr /lib /lib64

CapabilityBoundingSet=CAP_NET_BIND_SERVICE
AmbientCapabilities=CAP_NET_BIND_SERVICE

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable remote-agent
```

---

### ۴. شروع و وریفای

```bash
sudo systemctl start remote-agent
sudo systemctl status remote-agent --no-pager
sudo journalctl -u remote-agent -f --no-pager

# تست پورت
ss -tlnp | grep 8765

# تست لوکال
cd /opt/remote-agent
AGENT_TOKEN=$(grep AGENT_TOKEN /etc/remote-agent/server.env | cut -d= -f2)
export AGENT_TOKEN
./venv/bin/python -m client.cli --host 127.0.0.1 -c "echo 'Local OK'"
```

---

### ۵. TLS/SSL (برای اینترنت عمومی)

#### Self-signed (تست/داخلی)
```bash
sudo mkdir -p /etc/remote-agent/certs
sudo openssl req -x509 -newkey rsa:4096 -keyout /etc/remote-agent/certs/key.pem \
    -out /etc/remote-agent/certs/cert.pem -days 365 -nodes \
    -subj "/CN=remote-agent"
sudo chown remote-agent:remote-agent /etc/remote-agent/certs/*.pem
sudo chmod 600 /etc/remote-agent/certs/key.pem

sudo sed -i 's|# AGENT_TLS_CERT=|AGENT_TLS_CERT=/etc/remote-agent/certs/cert.pem|' /etc/remote-agent/server.env
sudo sed -i 's|# AGENT_TLS_KEY=|AGENT_TLS_KEY=/etc/remote-agent/certs/key.pem|' /etc/remote-agent/server.env
sudo systemctl restart remote-agent
```

#### Let's Encrypt (دامنه واقعی)
```bash
sudo apt install certbot
sudo certbot certonly --standalone -d agent.yourdomain.com

# در server.env:
# AGENT_TLS_CERT=/etc/letsencrypt/live/agent.yourdomain.com/fullchain.pem
# AGENT_TLS_KEY=/etc/letsencrypt/live/agent.yourdomain.com/privkey.pem

# تازه‌سازی خودکار
echo "0 3 * * * root certbot renew --quiet --post-hook 'systemctl reload remote-agent'" | sudo tee /etc/cron.d/certbot-remote-agent
```

**کلاینت با TLS:**
```bash
export AGENT_USE_TLS=true
export AGENT_CA_CERT=/path/to/cert.pem  # کپی cert.pem از سرور
agent --host YOUR_SERVER -i
```

---

### ۶. فایروال پیشرفته (IP محدود)

```bash
# حذف قانون پیش‌فرض
sudo ufw delete allow 8765/tcp

# فقط IPهای مجاز
sudo ufw allow from 203.0.113.0/24 to any port 8765 proto tcp comment 'Office IP'
sudo ufw allow from 192.168.1.0/24 to any port 8765 proto tcp comment 'VPN Range'
sudo ufw allow from YOUR_HOME_IP to any port 8765 proto tcp comment 'Home IP'

# یا iptables مستقیم
sudo iptables -A INPUT -p tcp -s YOUR_CLIENT_IP --dport 8765 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 8765 -j DROP
```

---

### ۷. Fail2Ban (محافظت brute-force)

```bash
sudo tee /etc/fail2ban/jail.d/remote-agent.conf > /dev/null <<'EOF'
[remote-agent]
enabled = true
port = 8765
filter = remote-agent
logpath = /var/log/remote-agent/server.log
maxretry = 5
bantime = 3600
findtime = 600
EOF

sudo tee /etc/fail2ban/filter.d/remote-agent.conf > /dev/null <<'EOF'
[Definition]
failregex = Authentication failed from <HOST>
            Invalid token from <HOST>
            Connection refused from <HOST>
ignoreregex =
EOF

sudo systemctl restart fail2ban
sudo fail2ban-client status remote-agent
```

---

### ۸. Logrotate (مدیریت لاگ‌ها)

```bash
sudo tee /etc/logrotate.d/remote-agent > /dev/null <<'EOF'
/var/log/remote-agent/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 640 remote-agent remote-agent
    sharedscripts
    postrotate
        systemctl reload remote-agent > /dev/null 2>&1 || true
    endscript
}
EOF

# تست
sudo logrotate -d /etc/logrotate.d/remote-agent
```

---

### ۹. کلاینت و پروفایل‌ها

```bash
# نصب کلاینت
pipx install git+https://github.com/Noperimme4/remote-agent.git

# پروفایل پیش‌فرض
mkdir -p ~/.config/remote-agent
cat > ~/.config/remote-agent/profiles.json <<EOF
{
  "profiles": {
    "prod": {
      "name": "prod",
      "host": "YOUR_SERVER_IP",
      "port": 8765,
      "token": "YOUR_TOKEN",
      "use_tls": true,
      "ca_cert": "~/certs/remote-agent-cert.pem",
      "timeout": 60,
      "cwd": "/data/workspace",
      "description": "Production Server"
    }
  },
  "current": "prod"
}
EOF
chmod 600 ~/.config/remote-agent/profiles.json
```

---

### ۱۰. چک‌لیست پروداکشن (قبل از Go-Live)

| مورد | چک | دستور |
|------|-----|-------|
| سرویس running | ☐ | `systemctl is-active remote-agent` |
| توکن امن ذخیره شده | ☐ | `cat /etc/remote-agent/server.env` |
| فایروال IP محدود | ☐ | `sudo ufw status numbered` |
| TLS فعال (اگر عمومی) | ☐ | `openssl s_client -connect IP:8765` |
| Logrotate کانفیگ | ☐ | `cat /etc/logrotate.d/remote-agent` |
| Fail2Ban فعال | ☐ | `sudo fail2ban-client status remote-agent` |
| بک‌آپ کانفیگ | ☐ | `tar -czf backup.tar.gz /etc/remote-agent` |
| تست کلاینت | ☐ | `agent --profile prod -c "echo OK"` |
| مانیتورینگ لاگ | ☐ | `journalctl -u remote-agent -f` |

---

### ۱۱. عیب‌یابی پروداکشن

| خطا | چک | راه‌حل |
|-----|-----|--------|
| `Address already in use` | `ss -tlnp \| grep 8765` | Kill PID قبلی |
| `Permission denied` | پرمیشن دایرکتوری‌ها | `chown -R remote-agent: /opt/remote-agent /data/workspace` |
| `Authentication failed` | توکن mismatch | توکن کلاینت/سرور یکسان باشد |
| `Command not allowed` | در ALLOWED_COMMANDS نیست | اضافه در `/etc/remote-agent/server.env` |
| `Timeout` | دستور طولانی | افزایش `AGENT_MAX_TIMEOUT` |

---

### ۱۲. آپدیت و حذف

```bash
# آپدیت سرور
cd /opt/remote-agent && sudo -u remote-agent git pull && sudo -u remote-agent ./venv/bin/pip install -r server/requirements.txt && sudo systemctl restart remote-agent

# آپدیت کلاینت
pipx upgrade remote-agent

# حذف کامل
sudo systemctl stop remote-agent && sudo systemctl disable remote-agent
sudo rm /etc/systemd/system/remote-agent.service && sudo systemctl daemon-reload
sudo rm -rf /opt/remote-agent /etc/remote-agent /var/log/remote-agent /data/workspace
sudo userdel remote-agent
sudo ufw delete allow 8765/tcp
pipx uninstall remote-agent
rm -rf ~/.config/remote-agent
```

---

## 🐳 نصب با Docker

### پیش‌نیاز
```bash
docker --version
docker compose version
```

### ۱. docker-compose.yml
```bash
cd remote-agent

cat > docker-compose.yml << 'EOF'
version: '3.8'
services:
  remote-agent:
    build: .
    container_name: remote-agent-server
    ports:
      - "8765:8765"
    environment:
      - AGENT_TOKEN=${AGENT_TOKEN}
      - AGENT_HOST=0.0.0.0
      - AGENT_PORT=8765
      - AGENT_LOG_LEVEL=INFO
      - AGENT_WORKDIR=/data/workspace
      - AGENT_ALLOW_SHELL=false
      - AGENT_ALLOW_FILES=true
    volumes:
      - ./data/workspace:/data/workspace
      - ./config:/etc/remote-agent
      - ./logs:/var/log/remote-agent
    restart: unless-stopped
    networks:
      - agent-net

networks:
  agent-net:
    driver: bridge
EOF
```

### ۲. توکن و استقرار
```bash
echo "AGENT_TOKEN=$(openssl rand -hex 32)" > .env
docker compose up -d
docker compose logs -f
```

### ۳. تست
```bash
export AGENT_TOKEN=$(cat .env | cut -d= -f2)
agent --host YOUR_SERVER_IP -c "echo 'Docker server working!'"
```

---

## 🪟 نصب روی Windows

### سرور (PowerShell Admin)

```powershell
# یک خط
irm https://raw.githubusercontent.com/Noperimme4/remote-agent/main/scripts/install_windows.ps1 | iex

# یا دستی
git clone https://github.com/Noperimme4/remote-agent.git
cd remote-agent
.\scripts\install_windows.ps1
```

**خروجی:** توکن در کنسول نمایش داده می‌شود. سرویس `RemoteAgent` نصب می‌شود.

```powershell
Start-Service RemoteAgent
Get-Service RemoteAgent
Get-Content "C:\ProgramData\RemoteAgent\logs\service.log" -Wait
```

### کلاینت روی Windows

```powershell
pipx install git+https://github.com/Noperimme4/remote-agent.git
# یا
pip install git+https://github.com/Noperimme4/remote-agent.git

$env:AGENT_TOKEN = "YOUR_TOKEN"
agent --host SERVER_IP -i
```

---

## 🔑 اتصال و استفاده

### ۱. تنظیم توکن
```bash
# Linux/macOS - موقت
export AGENT_TOKEN="your-token"

# Linux/macOS - دائمی
echo 'export AGENT_TOKEN="your-token"' >> ~/.bashrc
source ~/.bashrc
```

```powershell
# Windows PowerShell - موقت
$env:AGENT_TOKEN = "your-token"

# Windows PowerShell - دائمی
[Environment]::SetEnvironmentVariable("AGENT_TOKEN", "your-token", "User")
```

### ۲. حالت‌های استفاده

| دستور | توضیح |
|--------|--------|
| `agent --host IP -i` | منوی تعاملی کامل (پیش‌فرض) |
| `agent --host IP -c "cmd"` | اجرای دستور تکی |
| `agent --host IP --shell` | PTY Shell مستقیم |
| `agent --host IP --hermes` | چت با Hermes AI |
| `agent --host IP --files` | مرورگر فایل |
| `agent --host IP --profiles` | مدیریت پروفایل‌ها |
| `agent --profile NAME` | استفاده از پروفایل ذخیره شده |

### ۳. مثال‌های عملی
```bash
# لیست فایل‌ها
agent -c "ls -la /data"

# وضعیت داکر
agent -c "docker ps -a"

# استاتوس سرویس
agent -c "systemctl status nginx"

# لاگ‌ها
agent -c "journalctl -u sshd -n 50 --no-pager"

# مانیتورینگ
agent -c "top -bn1 | head -10"
agent -c "free -h && df -h /"
```

---

## 🎯 منوی تعاملی

```
╔═══════════════════════════════════════════════════════════════════╗
║                    🌐 Remote Agent Client v2.0                  ║
║         Secure Remote Control + Hermes AI Integration           ║
╚═══════════════════════════════════════════════════════════════════╝

🔗 Server: remote-agent-server
📍 Session: a1b2c3d4...
📂 Dir: /data/workspace

Key  Option              Description
1    🐚 PTY Shell        Full terminal (vim, htop, ssh, sudo)
2    🤖 Hermes AI Chat   Chat with Hermes AI on remote
3    📁 File Browser     Browse, upload, download files
4    ⚡ Quick Command    Run a single command
5    🐳 Docker Manager   Containers, images, logs
6    ⚙️  Services         systemctl start/stop/restart
7    📊 System Monitor   CPU, RAM, Disk, Processes
8    📝 View Logs        journalctl, dmesg, auth logs
9    🔧 Settings         Change dir, timeout, TLS
0    🚪 Exit             Disconnect and quit

Select option [1]: 
```

---

## ⌨️ تمام دستورات CLI

```bash
agent [OPTIONS]

Options:
  --host HOST         آدرس سرور (پیش‌فرض: localhost)
  --port PORT         پورت سرور (پیش‌فرض: 8765)
  --token TOKEN       توکن احراز هویت (یا AGENT_TOKEN env)
  --profile NAME      استفاده از پروفایل ذخیره شده
  --save-profile      ذخیره اتصال جاری به عنوان پروفایل
  -i, --interactive   منوی تعاملی (پیش‌فرض)
  -c, --command CMD   اجرای دستور تکی و خروج
  -s, --shell         PTY Shell مستقیم
  --hermes            چت با Hermes AI
  --files             مرور فایل‌ها
  --profiles          مدیریت پروفایل‌های سرور
  -v, --verbose       لاگ DEBUG
  -h, --help          راهنما

Environment Variables:
  AGENT_TOKEN         توکن پیش‌فرض
  AGENT_HOST          هاست پیش‌فرض
  AGENT_PORT          پورت پیش‌فرض
```

---

## 👤 مدیریت پروفایل‌ها

```bash
agent --profiles
```

```
🔧 Profile Manager

Current: myserver (192.168.1.100:8765) ⭐

#  Name        Host              Port  TLS  Description
1  myserver    192.168.1.100     8765  ✗    Production server
2  dev         10.0.0.5          8765  ✓    Development

Actions: a)dd  c)onnect  s)elect  e)dit  d)elete  q)uit
```

---

## ⚙️ تنظیمات سرور

### فایل: `/etc/remote-agent/server.env`

```ini
# Network
AGENT_HOST=0.0.0.0
AGENT_PORT=8765

# Authentication (REQUIRED)
AGENT_TOKEN=your-32-byte-hex-token

# Security - Allowed Commands
AGENT_ALLOWED_COMMANDS=ls,cat,head,tail,grep,find,ps,top,htop,df,du,free,uptime,whoami,pwd,date,python3,pip,git,docker,kubectl,systemctl,journalctl,ssh,scp,rsync,tar,zip,unzip,mkdir,cp,mv,rm,chmod,chown,ln,apt,apt-get,yum,dnf,pacman,pip3,npm,make,cmake,cargo,go,rustc,gcc,clang,vim,nano,less,more,bat,fd,rg

# Security - Blocked Commands
AGENT_BLOCKED_COMMANDS=reboot,shutdown,halt,poweroff,mkfs,fdisk,parted,dd,wipefs,cryptsetup,passwd,userdel,groupdel,visudo,chroot,pivot_root,kexec,mount,umount

# Limits
AGENT_MAX_TIMEOUT=300
AGENT_DEFAULT_TIMEOUT=60
AGENT_ALLOW_SHELL=false
AGENT_ALLOW_FILES=true

# Logging
AGENT_LOG_LEVEL=INFO
AGENT_LOG_FILE=/var/log/remote-agent/server.log

# Working Directory
AGENT_WORKDIR=/data/workspace

# TLS (Optional)
# AGENT_TLS_CERT=/etc/remote-agent/cert.pem
# AGENT_TLS_KEY=/etc/remote-agent/key.pem
```

---

## 🔐 امنیت

### بهترین شیوه‌ها
1. **توکن قوی:** `openssl rand -hex 32`
2. **TLS در تولید:** Self-signed یا Let's Encrypt
3. **فایروال:** پورت 8765 فقط از IPهای مورد اعتماد
4. **لیست سفید حداقل:** فقط دستورات ضروری در `ALLOWED_COMMANDS`
5. **محدودیت Shell:** `ALLOW_SHELL=false` (پیش‌فرض)
6. **لاگینگ:** `journalctl -u remote-agent -f`

---

## 🐛 عیب‌یابی سریع

| مشکل | راه‌حل |
|--------|--------|
| `Connection refused` | سرور اجرا شده؟ `systemctl status remote-agent` — پورت باز؟ فایروال؟ |
| `Authentication failed` | توکن در کلاینت/سرور یکسان؟ whitespace نداره؟ |
| `Command not allowed` | دستور در `ALLOWED_COMMANDS` هست؟ در `BLOCKED` نیست؟ |
| `Timeout` | `AGENT_MAX_TIMEOUT` یا `--timeout` را زیاد کنید |
| `ModuleNotFoundError: server.agent` | از ریشه پروژه اجرا کنید: `python -m server.agent` |

### لاگ‌ها
```bash
# Linux
journalctl -u remote-agent -f
tail -f /var/log/remote-agent/server.log

# Windows
Get-Content "C:\ProgramData\RemoteAgent\logs\service.log" -Wait

# Docker
docker compose logs -f remote-agent
```

---

## 📁 ساختار پروژه

```
remote-agent/
├── client/
│   ├── __main__.py          # Entry point (agent command)
│   ├── cli.py               # Core client logic
│   ├── menu.py              # Interactive menu (10 options)
│   ├── hermes.py            # Hermes AI Panel
│   ├── file_browser.py      # File browser
│   ├── pty_shell.py         # PTY terminal
│   ├── profile_manager.py   # Multi-server profiles
│   └── requirements.txt
├── server/
│   ├── agent.py             # Main server (asyncio + PTY)
│   ├── dashboard.py         # FastAPI web dashboard
│   ├── audit.py             # JSONL audit logging
│   └── requirements.txt
├── shared/
│   └── protocol.py          # Shared message types
├── scripts/
│   ├── install.sh           # One-line Linux installer
│   ├── install_windows.ps1  # Windows NSSM installer
│   └── install_linux.sh     # Legacy installer
├── docs/
│   ├── INSTALL_FA.md        # Persian guide
│   └── INSTALL_EN.md        # English guide
├── tests/
│   └── test_protocol.py
├── pyproject.toml
├── README.md
└── LICENSE
```

---

## 🤝 مشارکت

1. Fork کنید
2. شاخه بسازید: `git checkout -b feature/amazing-feature`
3. Commit کنید: `git commit -m 'Add amazing feature'`
4. Push کنید: `git push origin feature/amazing-feature`
5. Pull Request باز کنید

**استایل کد:** Ruff + Black + MyPy (CI)

---

## 📄 مجوز

**MIT License** — استفاده آزاد، تجاری، تغییر، توزیع.  
فایل `LICENSE` را ببینید.

---

## ⭐ حمایت

اگر مفید بود، ستاره دهید:

```bash
gh repo star Noperimme4/remote-agent
```

---

## ☕ دونیت (Donate)

پشتیبانی مالی به توسعه کمک می‌کند:

| شبکه | آدرس |
|--------|-----------|
| **TON** | `UQBChYa6MgPOBG9nhb__ndHGOpPyadZXrv06YKjWoU7tJnSp` |
| **USDT (BEP20/BSC)** | `0x5D423b248B299E1A97c7098Ef8DAfB0F130cC951` |

> آدرس‌ها فقط برای دریافت دونیت‌اند. هیچ کلید خصوصی درخواست نمی‌شود.

---

## 🙋 سوالات متداول

**س: تفاوت با SSH چیست؟**  
ج: SSH برای دسترسی کامل شل. Remote Agent برای **اتوماسیون، CI/CD، اجرای دستور کنترل‌شده** با لیست سفید، لاگینگ متمرکز، API.

**س: از اینترنت عمومی قابل استفاده؟**  
ج: بله، **با TLS و فایروال محدود IP**. بدون TLS ترافیک رمزنگاری نمی‌شود.

**س: sudo اجرا می‌کند؟**  
ج: بله، اگر `sudo` در `ALLOWED_COMMANDS` باشد و یوزر در `sudoers` با `NOPASSWD`. **با احتیاط.**

**س: ویندوز کلاینت پشتیبانی شده؟**  
ج: بله، کلاینت پایتون روی ویندوز/لینوکس/مک کار می‌کند. سرور هم روی ویندوز (سرویس) نصب می‌شود.

**س: روتیشن توکن چطور؟**  
ج: در `server.env` تغییر دهید و `systemctl restart remote-agent`. کلاینت‌ها توکن جدید بگیرند.

---

<div align="center">

**ساخته شده با ❤️ برای توسعه‌دهندگان و ادمین‌های سیستمی**

[گزارش باگ](https://github.com/Noperimme4/remote-agent/issues) • [درخواست ویژگی](https://github.com/Noperimme4/remote-agent/issues/new) • [مستندات](https://github.com/Noperimme4/remote-agent/tree/main/docs)

</div>