# 🌐 Remote Agent — اجرای دستور از راه دور، امن و چندپلتفرم

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20Windows%20%7C%20macOS-lightgrey.svg)](https://github.com/YOUR_USERNAME/remote-agent)

> **Remote Agent** یک ابزار خط فرمان (CLI) و سرور سبک‌وزن برای اجرای امن دستورات روی ماشین‌های از راه دور (VPS، سرورهای خانگی، CI/CD runners) است. از احراز هویت توکنی، لیست سفید دستورات، لاگینگ کامل، و پشتیبانی از TLS پشتیبانی می‌کند. نصب روی **Linux (systemd)**، **Windows (NSSM Service)** و **Docker** امکان‌پذیر است.

---

## ✨ ویژگی‌ها

| ویژگی | توضیح |
|----------|----------|
| 🔐 **احراز هویت توکنی** | توکن ۲۵۶‌بیت تصادفی، ارسال در هدر، بدون رمز در کانفیگ |
| 🛡 **لیست سفید/سیاه دستورات** | فقط دستورات مجاز اجرا می‌شوند، دستورات خطرناک مسدود |
| 📡 **استریم زنده خروجی** | دیدن `stdout`/`stderr` لحظه‌به‌لحظه در حالت تعاملی |
| 🐚 **پشتیبانی از Shell** | اختیاری: اجرای دستور در `bash -c` یا `powershell -c` |
| 📁 **عملیات فایل** | لیست کردن پوشه‌ها، آپلود/دانلود (در توسعه) |
| ❤️ **Heartbeat** | تشخیص قطع اتصال، تمیز کردن سشن‌های مرده |
| 📝 **لاگینگ کامل** | فایل لاگ، journalctl (Linux)، Event Viewer (Windows) |
| 🔒 **TLS/SSL** | رمزگذاری ترافیک با گواهی self-signed یا CA |
| 🐳 **Docker Ready** | ایمیج رسمی، docker-compose برای استقرار سریع |
| ⚡ **Async/Non-blocking** | مبتنی بر `asyncio`، مدیریت صدها اتصال همزمان |

---

## 🏗 معماری

```
┌─────────────────────┐      TLS/TCP :8765      ┌─────────────────────┐
│   Client (Local)    │ ──────────────────────► │   Server (Remote)   │
│  Python CLI Tool    │ ◄────────────────────── │  Asyncio Server     │
│                     │    JSON Messages        │                     │
│ • Auth (Token)      │                         │ • Command Executor  │
│ • Command Request   │                         │ • Allowlist Check   │
│ • Stream Handler    │                         │ • Process Manager   │
│ • Interactive Shell │                         │ • File Manager      │
└─────────────────────┘                         └─────────────────────┘
```

**پروتکل:** پیام‌های JSON با پیشوند طول (4 بایت big-endian).  
**فرمت پیام:** `{"type": "command_request", "request_id": "...", "command": "ls", "args": ["-la"], ...}`

---

## 🚀 نصب سریع

### ۱. پیش‌نیازها
- **Python 3.10+** (روی کلاینت و سرور)
- **Git** برای کلون ریپو

### ۲. کلون و نصب روی سرور (Linux)

```bash
# روی سرور مقصد (VPS، سرور خانگی، و...)
git clone https://github.com/YOUR_USERNAME/remote-agent.git
cd remote-agent

# اجرا به عنوان root (برای systemd، یوزر سرویس، دایرکتوری‌ها)
sudo ./scripts/install_linux.sh
```

**خروجی نصب:**
```
✅ Python 3.11 found
✅ User 'remote-agent' created
✅ App installed to /opt/remote-agent
✅ Config generated at /etc/remote-agent/server.env
✅ Systemd service installed

⚠️  TOKEN: a1b2c3d4e5f6... (این را کپی و در جای امن ذخیره کنید!)
```

```bash
# فعال‌سازی و شروع سرویس
sudo systemctl start remote-agent
sudo systemctl enable remote-agent
sudo systemctl status remote-agent
```

### ۳. نصب روی کلاینت (لوکال — Linux/macOS/Windows)

```bash
# روی ماشین خودتان
git clone https://github.com/YOUR_USERNAME/remote-agent.git
cd remote-agent

# نصب وابستگی‌های کلاینت
pip install -e .[client]
# یا
pip install click rich
```

### ۴. اتصال و تست

```bash
# متغیر محیطی توکن (امن‌تر از آرگومان)
export AGENT_TOKEN="a1b2c3d4e5f6..."  # توکنی که در مرحله ۲ گرفتید

# حالت تعاملی (Interactive Shell)
python -m client.cli --host YOUR_SERVER_IP -i

# یا اجرای دستور تکی
AGENT_TOKEN=$AGENT_TOKEN python -m client.cli --host YOUR_SERVER_IP -c "ls -la /data"
```

**خروجی حالت تعاملی:**
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

---

## 🪟 نصب روی Windows (سرور یا کلاینت)

### سرور به عنوان سرویس ویندوز

```powershell
# در PowerShell به عنوان Administrator
git clone https://github.com/YOUR_USERNAME/remote-agent.git
cd remote-agent
.\scripts\install_windows.ps1
```

**این اسکریپت:**
1. Python 3.11 را از `winget` نصب می‌کند (در صورت عدم وجود)
2. دایرکتوری `C:\Program Files\RemoteAgent` می‌سازد
3. محیط مجازی و وابستگی‌ها را نصب می‌کند
4. توکن تصادفی تولید و در `C:\ProgramData\RemoteAgent\server.env` ذخیره می‌کند
5. سرویس ویندوز `RemoteAgent` را با **NSSM** ثبت می‌کند
6. فایروال را برای پورت 8765 باز می‌کند

```powershell
# مدیریت سرویس
Start-Service RemoteAgent
Get-Service RemoteAgent
Get-Content "C:\ProgramData\RemoteAgent\logs\service.log" -Wait
```

### کلاینت روی ویندوز

```powershell
# در PowerShell
$env:AGENT_TOKEN = "YOUR_TOKEN"
python -m client.cli --host SERVER_IP -i
```

---

## 🐳 استقرار با Docker

### Docker Compose (توصیه شده)

```yaml
# docker-compose.yml
version: '3.8'
services:
  remote-agent:
    build: .
    container_name: remote-agent-server
    ports:
      - "8765:8765"
    environment:
      - AGENT_TOKEN=${AGENT_TOKEN}  # از .env بخوانید
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
    # TLS (اختیاری)
    # environment:
    #   - AGENT_TLS_CERT=/etc/remote-agent/cert.pem
    #   - AGENT_TLS_KEY=/etc/remote-agent/key.pem
    # volumes:
    #   - ./certs:/etc/remote-agent

networks:
  agent-net:
    driver: bridge
```

```bash
# تولید توکن و استقرار
echo "AGENT_TOKEN=$(openssl rand -hex 32)" > .env
docker compose up -d
docker compose logs -f
```

### Dockerfile

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# سیستم‌عامل مینیمم
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# کپی و نصب
COPY pyproject.toml .
COPY server/ server/
COPY shared/ shared/
COPY client/ client/

RUN pip install --no-cache-dir -e .[server]

# یوزر غیر روت
RUN useradd -r -u 1000 -m agent
USER agent

EXPOSE 8765
CMD ["python", "-m", "server.agent"]
```

---

## ⚙️ تنظیمات (Configuration)

### متغیرهای محیطی سرور

| متغیر | پیش‌فرض | توضیح |
|----------|---------|----------|
| `AGENT_HOST` | `0.0.0.0` | آدرس بایند |
| `AGENT_PORT` | `8765` | پورت سرور |
| `AGENT_TOKEN` | **الزامی** | توکن احراز هویت (hex 64-char) |
| `AGENT_ALLOWED_COMMANDS` | لیست پیش‌فرض | دستورات مجاز (کاما جدا) |
| `AGENT_BLOCKED_COMMANDS` | لیست پیش‌فرض | دستورات مسدود |
| `AGENT_MAX_TIMEOUT` | `300` | ماکزیمم تایم‌اوت (ثانیه) |
| `AGENT_DEFAULT_TIMEOUT` | `60` | تایم‌اوت پیش‌فرض |
| `AGENT_ALLOW_SHELL` | `false` | اجازه `bash -c` |
| `AGENT_ALLOW_FILES` | `true` | فعال‌سازی عملیات فایل |
| `AGENT_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `AGENT_LOG_FILE` | `/var/log/remote-agent/server.log` | مسیر فایل لاگ |
| `AGENT_WORKDIR` | `/data/workspace` | دایرکتوری کاری پیش‌فرض |
| `AGENT_TLS_CERT` | — | مسیر گواهی TLS |
| `AGENT_TLS_KEY` | — | مسیر کلید TLS |

### مثال `server.env`

```bash
# /etc/remote-agent/server.env
AGENT_HOST=0.0.0.0
AGENT_PORT=8765
AGENT_TOKEN=a1b2c3d4e5f678901234567890abcdef1234567890abcdef1234567890abcdef
AGENT_ALLOWED_COMMANDS=ls,cat,head,tail,grep,find,ps,top,df,du,free,uptime,whoami,pwd,date,python3,pip,git,docker,systemctl,journalctl,ssh,scp,rsync,tar,zip,unzip,mkdir,cp,mv,rm,chmod,chown,apt,apt-get,pip3,npm,make,cargo,go,vim,nano
AGENT_BLOCKED_COMMANDS=reboot,shutdown,halt,poweroff,mkfs,fdisk,dd,wipefs,passwd,userdel,visudo,mount,umount
AGENT_MAX_TIMEOUT=300
AGENT_DEFAULT_TIMEOUT=60
AGENT_ALLOW_SHELL=false
AGENT_ALLOW_FILES=true
AGENT_LOG_LEVEL=INFO
AGENT_LOG_FILE=/var/log/remote-agent/server.log
AGENT_WORKDIR=/data/workspace
```

### کلاینت — متغیرهای محیطی

| متغیر | پیش‌فرض | توضیح |
|----------|---------|----------|
| `AGENT_HOST` | `localhost` | آدرس سرور |
| `AGENT_PORT` | `8765` | پورت سرور |
| `AGENT_TOKEN` | **الزامی** | توکن احراز هویت |
| `AGENT_TIMEOUT` | `60` | تایم‌اوت دستور (ثانیه) |
| `AGENT_USE_TLS` | `false` | استفاده از TLS |
| `AGENT_VERIFY_TLS` | `true` | تأیید گواهی |
| `AGENT_CA_CERT` | — | مسیر CA برای TLS |

---

## 🛠 استفاده پیشرفته

### ۱. اجرای دستور با استریم زنده

```bash
# در کد پایتون خودتان
from client.cli import RemoteAgentClient, ClientConfig
import asyncio

async def run_deploy():
    config = ClientConfig.from_env()
    client = RemoteAgentClient(config)
    
    await client.connect()
    
    # callback برای خروجی زنده
    def on_chunk(chunk):
        if chunk.chunk_type in ("stdout", "stderr"):
            print(chunk.data, end="", flush=True)
    
    resp = await client.execute(
        "docker", ["compose", "up", "-d", "--build"],
        cwd="/opt/myapp",
        timeout=300,
        stream=True,
        progress_cb=on_chunk
    )
    
    print(f"\nExit: {resp.exit_code}")
    await client.disconnect()

asyncio.run(run_deploy())
```

### ۲. لیست فایل‌های ریموت

```python
files = await client.list_files("/var/log", recursive=True)
for f in files:
    print(f"{'📁' if f['is_dir'] else '📄'} {f['path']} ({f['size']} bytes)")
```

### ۳. اسکریپت Deploy اتوماتیک

```bash
#!/bin/bash
# deploy.sh — اجرا روی لوکال، دیپلوی روی سرور
set -e

AGENT_TOKEN="$1"
SERVER_IP="$2"
APP_DIR="/opt/myapp"

echo "🚀 Deploying to $SERVER_IP..."

AGENT_TOKEN="$AGENT_TOKEN" python -m client.cli \
  --host "$SERVER_IP" \
  -c "cd $APP_DIR && git pull && docker compose up -d --build && docker image prune -f"

echo "✅ Deploy complete"
```

---

## 🔐 امنیت

### بهترین شیوه‌ها

1. **توکن قوی:** همیشه از `openssl rand -hex 32` استفاده کنید
2. **TLS در تولید:** گواهی self-signed یا Let's Encrypt فعال کنید
3. **فایروال:** پورت 8765 فقط از IP‌های مورد اعتماد باز باشد
   ```bash
   # UFW
   ufw allow from 203.0.113.0/24 to any port 8765
   # یا Windows Firewall
   New-NetFirewallRule -DisplayName "RemoteAgent" -Direction Inbound -LocalPort 8765 -Protocol TCP -Action Allow -RemoteAddress 203.0.113.0/24
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

---

## 📁 ساختار پروژه

```
remote-agent/
├── client/
│   ├── __init__.py
│   └── cli.py              # کلاینت CLI (async، interactive shell)
├── server/
│   ├── __init__.py
│   ├── agent.py            # سرور اصلی (asyncio، session management)
│   └── requirements.txt    # وابستگی‌های سرور
├── shared/
│   ├── __init__.py
│   └── protocol.py         # پروتکل مشترک (پیام‌ها، دیتاکلاس‌ها)
├── scripts/
│   ├── install_linux.sh    # نصب‌کننده لینوکس (systemd)
│   └── install_windows.ps1 # نصب‌کننده ویندوز (NSSM service)
├── tests/                  # تست‌ها (pytest-asyncio)
├── docs/                   # مستندات اضافی
├── pyproject.toml          # تنظیمات بسته، lint، test
├── .gitignore
├── LICENSE
└── README.md               # این فایل
```

---

## 🧪 تست و توسعه

```bash
# کلون و تنظیم محیط توسعه
git clone https://github.com/YOUR_USERNAME/remote-agent.git
cd remote-agent
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# نصب وابستگی‌های توسعه
pip install -e .[dev]

# اجرای تست‌ها
pytest -v

# لینت و فرمت
ruff check .
ruff format .
mypy .

# تست دستی سرور/کلاینت
# ترمینال ۱:
AGENT_TOKEN=testtoken python -m server.agent

# ترمینال ۲:
AGENT_TOKEN=testtoken python -m client.cli --host localhost -i
```

---

## 📋 توابع CLI

| فلگ | توضیح |
|------|----------|
| `-h, --host HOST` | آدرس سرور (پیش‌فرض: localhost) |
| `-p, --port PORT` | پورت سرور (پیش‌فرض: 8765) |
| `--token TOKEN` | توکن احراز هویت (یا `AGENT_TOKEN` env) |
| `-c, --command CMD` | اجرای دستور تکی و خروج |
| `-i, --interactive` | حالت شل تعاملی |
| `--cwd DIR` | دایرکتوری کاری روی سرور |
| `--timeout SEC` | تایم‌اوت دستور (پیش‌فرض: 60) |
| `--shell` | اجرا در shell (bash/powershell) |
| `--tls` | فعال‌سازی TLS |
| `--ca-cert PATH` | فایل CA برای تأیید TLS |
| `-v, --verbose` | لاگ DEBUG |

---

## 🐛 عیب‌یابی

| مشکل | راه‌حل |
|---------|----------|
| `Connection refused` | سرور اجرا شده؟ پورت باز است؟ فایروال؟ |
| `Authentication failed` | توکن در کلاینت و سرور یکسان است؟ whitespace نداره؟ |
| `Command not allowed` | دستور در `AGENT_ALLOWED_COMMANDS` نیست یا در `BLOCKED` است |
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

## 🤝 مشارکت

1. Fork کنید
2. شاخه بسازید: `git checkout -b feature/amazing-feature`
3. Commit کنید: `git commit -m 'Add amazing feature'`
4. Push کنید: `git push origin feature/amazing-feature`
5. Pull Request باز کنید

**استایل کد:** Ruff + Black + MyPy (بررسی در CI)

---

## 🗺 نقشه راه (Roadmap)

- [ ] آپلود/دانلود فایل (SFTP-like)
- [ ] Reverse Shell واقعی (PTY) با تغییر سایز ترمینال
- [ ] وب‌ یوآی برای مانیتورینگ سشن‌ها
- [ ] پشتیبانی از چند سرور در کلاینت (پروفایل‌ها)
- [ ] Плаگین برای VS Code / JetBrains (Remote Development)
- [ ] metaparticle.io integration برای Kubernetes
- [ ] Audit logging (JSONL) برای SIEM

---

## 📄 مجوز

**MIT License** — استفاده آزاد، تجاری، تغییر، توزیع.  
فایل `LICENSE` را ببینید.

---

## ⭐ حمایت

اگر این پروژه برایتان مفید بود، ستاره دادن روی گیت‌هاب باعث خوشحالی ماست!

```bash
gh repo star YOUR_USERNAME/remote-agent
```

---

## 🙋 سوالات متداول

**س: تفاوت با SSH چیست؟**  
ج: SSH برای دسترسی کامل شل طراحی شده. Remote Agent برای **اتوماسیون، CI/CD، و اجرای دستور کنترل‌شده** با لیست سفید، لاگینگ متمرکز، و API برنامه‌نویسی‌پذیر ساخته شده. completar نمی‌کند.

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

[گزارش باگ](https://github.com/YOUR_USERNAME/remote-agent/issues) • [درخواست ویژگی](https://github.com/YOUR_USERNAME/remote-agent/issues/new) • [مستندات کامل](https://github.com/YOUR_USERNAME/remote-agent/tree/main/docs)

</div>