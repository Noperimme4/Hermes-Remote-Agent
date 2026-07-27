# 🚀 راهنمای نصب آسان Remote Agent

> **یک خط، نصب کامل سرور + کلاینت**  
> پشتیبانی: Ubuntu/Debian/CentOS/RHEL/Fedora/Arch/Alpine

---

## ⚡ نصب سریع (سرور)

```bash
curl -fsSL https://raw.githubusercontent.com/Noperimme4/remote-agent/main/scripts/install.sh | sudo bash
```

**خروجی نمونه:**
```
[✓] Python 3.11 ready
[✓] User remote-agent ready
[✓] Code downloaded
[✓] Dependencies installed
[✓] Config written to /etc/remote-agent/server.env
[✓] Systemd service installed
[✓] Service started successfully!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔑 YOUR TOKEN (SAVE THIS!)
   a1b2c3d4e5f678901234567890abcdef1234567890abcdef1234567890abcdef
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Server IP: 203.0.113.10
Port: 8765

Client usage:
  export AGENT_TOKEN="a1b2c3d4e5f6..."
  python -m client.cli --host 203.0.113.10 -i
```

---

## 💻 نصب کلاینت (سیستم شما)

### روش ۱: pipx (توصیه شده - ایزوله)
```bash
pipx install git+https://github.com/Noperimme4/remote-agent.git
# یا
pipx install --editable ./remote-agent  # اگر کلون کردید
```

### روش ۲: pip (سراسری)
```bash
pip install git+https://github.com/Noperimme4/remote-agent.git
```

### روش ۳: کلون دستی
```bash
git clone https://github.com/Noperimme4/remote-agent.git
cd remote-agent
pip install -e .[client]
```

---

## 🔗 اتصال و استفاده

### ۱. متغیر محیطی توکن
```bash
# Linux/macOS
export AGENT_TOKEN="your-token-here"

# PowerShell (Windows)
$env:AGENT_TOKEN = "your-token-here"

# CMD (Windows)
set AGENT_TOKEN=your-token-here
```

### ۲. حالت تعاملی (Interactive Shell)
```bash
# Linux/macOS
python -m client.cli --host YOUR_SERVER_IP -i

# Windows PowerShell
python -m client.cli --host YOUR_SERVER_IP -i
```

### ۳. اجرای دستور تکی
```bash
python -m client.cli --host YOUR_SERVER_IP -c "ls -la /data"
python -m client.cli --host YOUR_SERVER_IP -c "docker ps"
```

### ۴. با TLS (اگر سرور گواهی داره)
```bash
python -m client.cli --host YOUR_SERVER_IP --tls --ca-cert ca.pem -i
```

---

## 📋 دستورات مفید سرور

```bash
# وضعیت سرویس
systemctl status remote-agent

# لاگ زنده
journalctl -u remote-agent -f

# ریستارت
sudo systemctl restart remote-agent

# تنظیمات
cat /etc/remote-agent/server.env

# تغییر توکن (سپس restart)
sudo nano /etc/remote-agent/server.env
sudo systemctl restart remote-agent
```

---

## 🔧 تنظیمات پیشرفته

### فایل کانفیگ: `/etc/remote-agent/server.env`

```ini
# شبکه
AGENT_HOST=0.0.0.0
AGENT_PORT=8765

# احراز هویت (اجباری)
AGENT_TOKEN=your-32-byte-hex-token

# امنیت
AGENT_ALLOWED_COMMANDS=ls,cat,git,docker,python3,pip,systemctl,...
AGENT_BLOCKED_COMMANDS=reboot,shutdown,mkfs,dd,passwd,...
AGENT_ALLOW_SHELL=false        # true = اجازه bash -c
AGENT_ALLOW_FILES=true         # عملیات فایل

# لاگ
AGENT_LOG_LEVEL=INFO           # DEBUG, INFO, WARNING, ERROR
AGENT_LOG_FILE=/var/log/remote-agent/server.log

# دایرکتوری کاری
AGENT_WORKDIR=/data/workspace

# TLS (اختیاری)
# AGENT_TLS_CERT=/etc/remote-agent/cert.pem
# AGENT_TLS_KEY=/etc/remote-agent/key.pem
```

### فایروال (فقط IP کلاینت اجازه دهید)
```bash
# UFW
sudo ufw allow from YOUR_CLIENT_IP to any port 8765

# iptables
sudo iptables -A INPUT -p tcp -s YOUR_CLIENT_IP --dport 8765 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 8765 -j DROP
```

### گواهی TLS با Let's Encrypt
```bash
sudo certbot certonly --standalone -d agent.yourdomain.com
# سپس در server.env:
AGENT_TLS_CERT=/etc/letsencrypt/live/agent.yourdomain.com/fullchain.pem
AGENT_TLS_KEY=/etc/letsencrypt/live/agent.yourdomain.com/privkey.pem
sudo systemctl restart remote-agent
```

---

## 🪟 نصب روی Windows (سرور)

```powershell
# در PowerShell به عنوان Administrator
irm https://raw.githubusercontent.com/Noperimme4/remote-agent/main/scripts/install_windows.ps1 | iex
```

یا دستی:
```powershell
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

---

## 🐳 Docker (اختیاری)

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

## ❓ عیب‌یابی سریع

| مشکل | راه‌حل |
|--------|--------|
| `Connection refused` | سرویس اجرا شده؟ `systemctl status remote-agent` |
| `Authentication failed` | توکن در کلاینت و سرور یکسان است؟ whitespace نداره؟ |
| `Command not allowed` | دستور در `AGENT_ALLOWED_COMMANDS` هست؟ |
| `Timeout` | `AGENT_MAX_TIMEOUT` یا `--timeout` زیادتر کنید |
| `Module not found` | `pip install -e .[client]` اجرا کردید؟ |

---

## 📚 منابع بیشتر

- **مستندات کامل:** https://github.com/Noperimme4/remote-agent#readme
- **گزارش باگ:** https://github.com/Noperimme4/remote-agent/issues
- **امنیت:** توکن رو در فایل `.env` یا keyring ذخیره کنید، نه در تاریخچه شل

---

<div align="center">
<strong>ساخته شده با ❤️ برای توسعه‌دهندگان ایران</strong>
</div>