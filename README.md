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

- [⚡ نصب آسان (یک خط)](#-نصب-آسان-یک-خط)
  - [سرور (Linux)](#سرور-linux)
  - [کلاینت (همه پلتفرم‌ها)](#کلاینت-همه-پلتفرم‌ها)
- [📖 نصب کامل (مرحله به مرحله برای مبتدیان)](#-نصب-کامل-مرحله-به-مرحله-برای-مبتدیان)
  - [پیش‌نیازها](#پیش‌نیازها)
  - [مرحله ۱: کلون ریپو](#مرحله-۱-کلون-ریپو)
  - [مرحله ۲: نصب سرور روی لینوکس](#مرحله-۲-نصب-سرور-روی-لینوکس)
  - [مرحله ۳: شروع سرویس و گرفتن توکن](#مرحله-۳-شروع-سرویس-و-گرفتن-توکن)
  - [مرحله ۴: نصب کلاینت روی سیستم خودتان](#مرحله-۴-نصب-کلاینت-روی-سیستم-خودتان)
  - [مرحله ۵: اتصال و تست](#مرحله-۵-اتصال-و-تست)
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

## ⚡ نصب آسان (یک خط)

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
# سرویس را شروع کنید
sudo systemctl start remote-agent
sudo systemctl enable remote-agent
```

---

### کلاینت (همه پلتفرم‌ها)

#### 🐧 Linux / macOS

```bash
# روش ۱: pipx (توصیه شده - ایزوله)
pipx install git+https://github.com/Noperimme4/remote-agent.git

# روش ۲: pip (سراسری)
pip install git+https://github.com/Noperimme4/remote-agent.git
```

#### 🪟 Windows (PowerShell)

```powershell
# روش ۱: pipx
pipx install git+https://github.com/Noperimme4/remote-agent.git

# روش ۲: pip
pip install git+https://github.com/Noperimme4/remote-agent.git
```

#### ✅ تست سریع کلاینت

```bash
# توکن را تنظیم کنید (از خروجی نصب سرور کپی کنید)
export AGENT_TOKEN="your-token-here"

# اتصال تستی
agent --host YOUR_SERVER_IP -c "echo 'Connected successfully!'"
```

---

## 📖 نصب کامل (مرحله به مرحله برای مبتدیان)

> **برای کسانی که می‌خواهند هر مرحله را درک کنند** — توضیح کامل، عکس‌های خروجی، و چک‌لیست.

---

### پیش‌نیازها

| مورد | توضیح | چک |
|------|--------|-----|
| **Python 3.10+** | روی هر دو ماشین (سرور و کلاینت) | ☐ |
| **Git** | برای کلون ریپو | ☐ |
| **دسترسی sudo/root** | فقط روی سرور برای نصب سرویس | ☐ |
| **اینترنت** | برای دانلود کد و وابستگی‌ها | ☐ |

**بررسی پیش‌نیازها:**

```bash
# روی هر دو ماشین
python3 --version   # باید 3.10 یا بالاتر باشد
git --version       # باید نصب باشد
```

---

### مرحله ۱: کلون ریپو

روی **هر دو ماشین** (سرور و کلاینت) اجرا کنید:

```bash
git clone https://github.com/Noperimme4/remote-agent.git
cd remote-agent
```

**خروجی مورد انتظار:**
```bash
Cloning into 'remote-agent'...
remote: Enumerating objects: 150, done.
remote: Counting objects: 100% (150/150), done.
Receiving objects: 100% (150/150), 200.00 KiB, done.
Resolving deltas: 100% (50/50), done.
```

---

### مرحله ۲: نصب سرور روی لینوکس

**فقط روی سرور (VPS، سرور خانگی، CI/CD runner) اجرا کنید:**

```bash
# وارد پوشه شوید
cd remote-agent

# اسکریپت نصب را اجرا کنید (نیاز به sudo دارد)
sudo ./scripts/install.sh
```

**چی اتفاق می‌افتد؟** (اسکریپت به صورت خودکار انجام می‌دهد):
1. ✅ چک می‌کند Python 3.10+ هست یا نه (نیاز باشد نصب می‌کند)
2. ✅ یوزر `remote-agent` می‌سازد (امنیت: غیر روت)
3. ✅ کد را دانلود می‌کند به `/opt/remote-agent`
4. ✅ محیط مجازی Python می‌سازد و وابستگی‌ها نصب می‌کند
5. ✅ فایل کانفیگ می‌سازد در `/etc/remote-agent/server.env`
6. ✅ سرویس systemd می‌سازد: `remote-agent.service`
7. ✅ **توکن ۶۴ کاراکتر هگز تولید می‌کند و نشان می‌دهد**

---

### مرحله ۳: شروع سرویس و گرفتن توکن

پس از اجرای اسکریپت، **توکن را کپی کنید** (فقط یک بار نمایش داده می‌شود!):

```bash
# سرویس را شروع کنید
sudo systemctl start remote-agent

# فعال کنید تا بعد از ریبوت خودکار بالا بیاید
sudo systemctl enable remote-agent

# وضعیت را چک کنید
sudo systemctl status remote-agent
```

**خروجی موفق `systemctl status`:**
```
● remote-agent.service - Remote Agent Server
     Loaded: loaded (/etc/systemd/system/remote-agent.service; enabled)
     Active: active (running) since Mon 2026-07-27 10:00:00 UTC; 5s ago
   Main PID: 12345 (python)
      Tasks: 1 (limit: 1000)
     Memory: 45.0M
     CGroup: /system.slice/remote-agent.service
             └─12345 /opt/remote-agent/venv/bin/python -m server.agent
```

**لاگ زنده برای عیب‌یابی:**
```bash
journalctl -u remote-agent -f
```

---

### مرحله ۴: نصب کلاینت روی سیستم خودتان

روی **لپتاپ/دسکتاپ خودتان** (نه سرور):

```bash
# در پوشه کلون شده
cd remote-agent

# روش ۱: pipx (توصیه شده - جدا از سیستم)
pipx install git+https://github.com/Noperimme4/remote-agent.git

# روش ۲: pip (نصب سراسری)
pip install git+https://github.com/Noperimme4/remote-agent.git

# روش ۳: توسعه (editable)
pip install -e .[client]
```

**تست نصب:**
```bash
agent --help
```

**خروجی:**
```
Usage: agent [OPTIONS]

Options:
  --host HOST         Server hostname/IP (default: localhost)
  --port PORT         Server port (default: 8765)
  --token TOKEN       Auth token (or set AGENT_TOKEN env)
  ...
```

---

### مرحله ۵: اتصال و تست

**۱. متغیر محیطی توکن را تنظیم کنید:**

```bash
# Linux/macOS
export AGENT_TOKEN="a1b2c3d4e5f678901234567890abcdef1234567890abcdef1234567890abcdef"

# Windows PowerShell
$env:AGENT_TOKEN = "a1b2c3d4e5f678901234567890abcdef1234567890abcdef1234567890abcdef"

# Windows CMD
set AGENT_TOKEN=a1b2c3d4e5f678901234567890abcdef1234567890abcdef1234567890abcdef
```

**۲. اتصال تستی (دستور تکی):**

```bash
agent --host YOUR_SERVER_IP -c "echo 'Hello from remote!'"
```

**۳. حالت تعاملی (منوی کامل):**

```bash
agent --host YOUR_SERVER_IP -i
# یا فقط
agent --host YOUR_SERVER_IP
```

**خروجی مورد انتظار:**
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

**✅ تبریک! همه چیز کار می‌کند.**

---

## 🐳 نصب با Docker

### پیش‌نیاز: Docker و Docker Compose

```bash
# چک کنید
docker --version
docker compose version
```

### ۱. فایل docker-compose.yml بسازید

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

### ۲. توکن تولید و استقرار کنید

```bash
# توکن تصادفی تولید کنید
echo "AGENT_TOKEN=$(openssl rand -hex 32)" > .env

# کانتینر را بالا بیاورید
docker compose up -d

# لاگ‌ها را ببینید
docker compose logs -f
```

### ۳. تست اتصال

```bash
export AGENT_TOKEN=$(cat .env | cut -d= -f2)
agent --host YOUR_SERVER_IP -c "echo 'Docker server working!'"
```

---

## 🪟 نصب روی Windows

### سرور (PowerShell به عنوان Administrator)

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
# مدیریت سرویس
Start-Service RemoteAgent
Get-Service RemoteAgent
Get-Content "C:\ProgramData\RemoteAgent\logs\service.log" -Wait
```

### کلاینت روی Windows

```powershell
# نصب
pipx install git+https://github.com/Noperimme4/remote-agent.git

# یا
pip install git+https://github.com/Noperimme4/remote-agent.git

# اتصال
$env:AGENT_TOKEN = "YOUR_TOKEN"
agent --host SERVER_IP -i
```

---

## 🔑 اتصال و استفاده

### ۱. تنظیم توکن (هر بار یا در `.bashrc`/پروفایل PowerShell)

```bash
# Linux/macOS - موقت
export AGENT_TOKEN="your-token"

# Linux/macOS - دائمی (به ~/.bashrc اضافه کنید)
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

هنگام اجرای `agent` یا `agent -i`، منوی زیر نمایش داده می‌شود:

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

### جزئیات هر گزینه:

| کلید | گزینه | توضیح |
|------|--------|--------|
| **1** | 🐚 **PTY Shell** | ترمینال کامل با پشتیبانی `vim`، `htop`، `ssh`، `sudo`، `docker exec -it`، `nano`، `top` |
| **2** | 🤖 **Hermes AI Chat** | چت با Hermes AI روی سرور ریموت (دستورات: `/new`، `/history`، `/save`، `/help`) |
| **3** | 📁 **File Browser** | مرور فایل‌ها، آپلود/دانلود (base64)، مشاهده، حذف، ساخت پوشه |
| **4** | ⚡ **Quick Command** | اجرای دستور تکی با استریم زنده خروجی |
| **5** | 🐳 **Docker Manager** | `docker ps`، `images`، `logs`، `start/stop/restart`، `stats` |
| **6** | ⚙️ **Services** | `systemctl list/start/stop/restart/enable/disable/status`، `journalctl -u` |
| **7** | 📊 **System Monitor** | `top`، `free -h`، `df -h`، `uptime`، `ps aux` |
| **8** | 📝 **View Logs** | `journalctl`، `dmesg`، `sshd logs`، custom service logs |
| **9** | 🔧 **Settings** | تغییر دایرکتوری کاری، تایم‌اوت، فعال/غیرفعال TLS |
| **0** | 🚪 **Exit** | قطع اتصال و خروج |

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

### مثال‌ها:

```bash
# اتصال با توکن و هاست
agent --host 192.168.1.100 --token abc123

# استفاده از پروفایل ذخیره شده
agent --profile myserver

# اجرای دستور تکی
agent -c "ls -la /data"
agent -c "docker ps -a"
agent -c "systemctl status nginx"

# PTY Shell مستقیم
agent --shell

# Hermes AI Chat
agent --hermes

# File Browser
agent --files

# مدیریت پروفایل‌ها
agent --profiles

# ذخیره پروفایل جدید
agent --host 192.168.1.100 --token abc123 --save-profile
```

---

## 👤 مدیریت پروفایل‌ها

```bash
# ورود به مدیریت پروفایل‌ها
agent --profiles
```

منوی پروفایل‌ها:
```
🔧 Profile Manager

Current: myserver (192.168.1.100:8765) ⭐

#  Name        Host              Port  TLS  Description
1  myserver    192.168.1.100     8765  ✗    Production server
2  dev         10.0.0.5          8765  ✓    Development

Actions: a)dd  c)onnect  s)elect  e)dit  d)elete  q)uit
```

**عملیات:**
- `a` — پروفایل جدید اضافه کنید
- `c` — به پروفایل انتخاب شده وصل شوید
- `s` — به عنوان پیش‌فرض انتخاب کنید
- `e` — ویرایش کنید
- `d` — حذف کنید

---

## ⚙️ تنظیمات سرور

### فایل کانفیگ: `/etc/remote-agent/server.env`

```ini
# Network
AGENT_HOST=0.0.0.0
AGENT_PORT=8765

# Authentication (REQUIRED)
AGENT_TOKEN=your-32-byte-hex-token

# Security - Allowed Commands (comma-separated)
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

# TLS (Optional - for production)
# AGENT_TLS_CERT=/etc/remote-agent/cert.pem
# AGENT_TLS_KEY=/etc/remote-agent/key.pem
```

### متغیرهای مهم

| متغیر | پیش‌فرض | توضیح |
|----------|---------|----------|
| `AGENT_TOKEN` | **الزامی** | توکن ۶۴ کاراکتر هگز |
| `AGENT_ALLOWED_COMMANDS` | لیست پیش‌فرض | دستورات مجاز (کاما جدا) |
| `AGENT_BLOCKED_COMMANDS` | لیست پیش‌فرض | دستورات مسدود |
| `AGENT_ALLOW_SHELL` | `false` | اجازه `bash -c` |
| `AGENT_MAX_TIMEOUT` | `300` | ماکزیمم تایم‌اوت (ثانیه) |
| `AGENT_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

### اعمال تغییرات

```bash
sudo systemctl restart remote-agent
```

---

## 🔐 امنیت

### بهترین شیوه‌ها

1. **توکن قوی:** همیشه از `openssl rand -hex 32` استفاده کنید
2. **TLS در تولید:** گواهی self-signed یا Let's Encrypt فعال کنید
3. **فایروال:** پورت 8765 فقط از IP‌های مورد اعتماد باز باشد
   ```bash
   # UFW
   sudo ufw allow from YOUR_CLIENT_IP to any port 8765
   
   # iptables
   sudo iptables -A INPUT -p tcp -s YOUR_CLIENT_IP --dport 8765 -j ACCEPT
   sudo iptables -A INPUT -p tcp --dport 8765 -j DROP
   ```
4. **لیست سفید حداقل:** فقط دستورات ضروری را در `AGENT_ALLOWED_COMMANDS` بگذارید
5. **محدودیت Shell:** `AGENT_ALLOW_SHELL=false` (پیش‌فرض) — جلوی تزریق دستور را می‌گیرد
6. **لاگینگ:** لاگ‌ها را مانیتور کنید (`journalctl -u remote-agent -f`)

### تولید گواهی TLS

```bash
# Self-signed برای تست/داخلی
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes -subj "/CN=remote-agent"

# در کانفیگ
AGENT_TLS_CERT=/etc/remote-agent/cert.pem
AGENT_TLS_KEY=/etc/remote-agent/key.pem

# کلاینت با TLS
AGENT_USE_TLS=true AGENT_CA_CERT=cert.pem python -m client.cli --host SERVER -i
```

### Let's Encrypt (تولید)

```bash
sudo certbot certonly --standalone -d agent.yourdomain.com
# سپس در server.env:
AGENT_TLS_CERT=/etc/letsencrypt/live/agent.yourdomain.com/fullchain.pem
AGENT_TLS_KEY=/etc/letsencrypt/live/agent.yourdomain.com/privkey.pem
sudo systemctl restart remote-agent
```

---

## 🐛 عیب‌یابی سریع

| مشکل | راه‌حل |
|--------|--------|
| `Connection refused` | سرور اجرا شده؟ `systemctl status remote-agent` — پورت باز است؟ فایروال؟ |
| `Authentication failed` | توکن در کلاینت و سرور یکسان است؟ whitespace نداره؟ |
| `Command not allowed` | دستور در `AGENT_ALLOWED_COMMANDS` هست؟ در `BLOCKED` نیست؟ |
| `Timeout` | `AGENT_MAX_TIMEOUT` یا `--timeout` را زیاد کنید |
| `ModuleNotFoundError: server.agent` | از ریشه پروژه اجرا کنید: `python -m server.agent` |
| Windows: `NSSM not found` | اسکریپت نصب NSSM را دانلود می‌کند، اینترنت چک کنید |

### لاگ‌ها

```bash
# Linux (systemd)
journalctl -u remote-agent -f
tail -f /var/log/remote-agent/server.log

# Windows
Get-Content "C:\ProgramData\RemoteAgent\logs\service.log" -Wait
Get-WinEvent -LogName Application -ProviderName "RemoteAgent" -MaxEvents 50

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
│   ├── hermes.py            # Hermes AI Panel (full featured)
│   ├── file_browser.py      # File browser (up/download/view)
│   ├── pty_shell.py         # PTY terminal emulation
│   ├── profile_manager.py   # Multi-server profiles
│   └── requirements.txt
├── server/
│   ├── agent.py             # Main server (asyncio + PTY)
│   ├── dashboard.py         # FastAPI web dashboard
│   ├── audit.py             # JSONL audit logging
│   └── requirements.txt
├── shared/
│   └── protocol.py          # Shared message types (PTY + File + Shell)
├── scripts/
│   ├── install.sh           # One-line Linux installer
│   ├── install_windows.ps1  # Windows NSSM service installer
│   └── install_linux.sh     # Legacy systemd installer
├── docs/
│   ├── INSTALL_FA.md        # Persian guide
│   └── INSTALL_EN.md        # English guide
├── tests/
│   └── test_protocol.py     # 9 tests passing
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

**استایل کد:** Ruff + Black + MyPy (بررسی در CI)

---

## 📄 مجوز

**MIT License** — استفاده آزاد، تجاری، تغییر، توزیع.  
فایل `LICENSE` را ببینید.

---

## ⭐ حمایت

اگر این پروژه برایتان مفید بود، ستاره دادن روی گیت‌هاب باعث خوشحالی ماست!

```bash
gh repo star Noperimme4/remote-agent
```

---

## ☕ دونیت (Donate)

پشتیبانی مالی شما به ادامه توسعه و نگهداری این پروژه کمک می‌کند. هر مبلغی، کوچک یا بزرگ، قدردان هستیم!

| شبکه | آدرس / QR |
|--------|-----------|
| **TON** | `UQBChYa6MgPOBG9nhb__ndHGOpPyadZXrv06YKjWoU7tJnSp` |
| **USDT (BEP20 / BSC)** | `0x5D423b248B299E1A97c7098Ef8DAfB0F130cC951` |

> **نکته:** آدرس‌های بالا فقط برای دریافت دونیت هستند. هیچ کلید خصوصی یا عبارتی درخواست نمی‌شود.

---

## 🙋 سوالات متداول

**س: تفاوت با SSH چیست؟**  
ج: SSH برای دسترسی کامل شل طراحی شده. Remote Agent برای **اتوماسیون، CI/CD، و اجرای دستور کنترل‌شده** با لیست سفید، لاگینگ متمرکز، و API برنامه‌نویسی‌پذیر ساخته شده. SSH را completar نمی‌کند.

**س: می‌توانم از طریق اینترنت عمومی استفاده کنم؟**  
ج: بله، **با TLS و فایروال محدودکننده IP**. بدون TLS ترافیک رمزنگاری نمی‌شود.

**س: آیا می‌تواند sudo اجرا کند؟**  
ج: بله، اگر `sudo` در `AGENT_ALLOWED_COMMANDS` باشد و یوزر سرویس در `sudoers` با `NOPASSWD` تنظیم شده باشد. **با احتیاط استفاده کنید.**

**س: ویندوز کلاینت هم پشتیبانی می‌شود؟**  
ج: بله، کلاینت پایتون روی ویندوز، لینوکس، مک کار می‌کند. سرور هم روی ویندوز (به عنوان سرویس) نصب می‌شود.

**س: چطور توکن را روتیت (تغییر) دهم؟**  
ج: در فایل کانفیگ سرور `AGENT_TOKEN` را تغییر دهید و سرویس را ریستارت کنید. کلاینت‌ها باید توکن جدید را بگیرند.

---

<div align="center">

**ساخته شده با ❤️ برای توسعه‌دهندگان و ادمین‌های سیستمی**

[گزارش باگ](https://github.com/Noperimme4/remote-agent/issues) • [درخواست ویژگی](https://github.com/Noperimme4/remote-agent/issues/new) • [مستندات کامل](https://github.com/Noperimme4/remote-agent/tree/main/docs)

</div>