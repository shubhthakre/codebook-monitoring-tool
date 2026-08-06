# Codebook Monitoring Tool

A lightweight health-check dashboard for servers, databases, Oracle, SQLite, and systemd service logs.

## Stack

- **Frontend:** Next.js 15 (App Router)
- **Backend:** FastAPI + APScheduler
- **Storage:** SQLite (single file, no external DB required)

## Features

- Add monitors for HTTP endpoints, TCP ports, PostgreSQL, MySQL, SQLite, Oracle, and systemd logs
- Automatic periodic checks with configurable intervals
- Manual "Check Now" with response time tracking
- Check history per monitor
- Systemd log viewer (Linux hosts with `journalctl`)
- Email alerts when a service goes down (and optional recovery emails)

For production setup (services, reverse proxy, backups, Oracle client), see [DEPLOYMENT.md](./DEPLOYMENT.md).

## Quick Start

### 1. Backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate

pip install -r requirements.txt

# Optional: enable email alerts
copy .env.example .env   # Windows
# cp .env.example .env   # Linux/macOS
# Edit .env with your SMTP settings

uvicorn app.main:app --reload --port 8000
```

Optional database drivers (install only what you need):

```bash
pip install psycopg2-binary   # PostgreSQL
pip install pymysql           # MySQL
pip install oracledb          # Oracle
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

## Monitor Types

| Type       | Config fields                                      |
|------------|----------------------------------------------------|
| `http`     | url, method, expected_status, timeout              |
| `tcp`      | host, port, timeout                                |
| `postgres` | host, port, database, user, password, query        |
| `mysql`    | host, port, database, user, password, query        |
| `sqlite`   | path, query                                        |
| `oracle`   | host, port, service_name, user, password, dsn      |
| `systemd`  | unit, lines, since                                 |

## Email Alerts

When a monitor transitions to **down**, the backend can send an email. A recovery email is sent when it returns to **up** (configurable).

1. Copy `backend/.env.example` to `backend/.env`
2. Set SMTP and recipient values:

| Variable | Description |
|----------|-------------|
| `ALERT_ENABLED` | `true` to turn alerts on |
| `ALERT_TO` | Comma-separated recipient emails |
| `ALERT_FROM` | From address |
| `ALERT_ON_RECOVERY` | Also email when service recovers (`true`/`false`) |
| `ALERT_COOLDOWN_SECONDS` | Min seconds between repeated down alerts (default `300`) |
| `SMTP_HOST` / `SMTP_PORT` | SMTP server |
| `SMTP_USER` / `SMTP_PASSWORD` | SMTP auth (leave empty if none) |
| `SMTP_USE_TLS` | STARTTLS (typical for port 587) |
| `SMTP_USE_SSL` | Implicit SSL (typical for port 465) |

Alerts fire only on status **transitions** (not on every failed check). Email failures are logged and do not break health checks.

Example Gmail (use an [App Password](https://support.google.com/accounts/answer/185833)):

```env
ALERT_ENABLED=true
ALERT_TO=you@example.com
ALERT_FROM=you@example.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@example.com
SMTP_PASSWORD=your-app-password
SMTP_USE_TLS=true
```

## Systemd Notes

Systemd log checks require:

- Linux host
- `journalctl` and `systemctl` in PATH
- Permission to read the target unit's journal

On Windows, systemd monitors will report that Linux is required.

## Project Structure

```
backend/
  app/
    checkers/     # Health check implementations
    routers/      # API routes
    services/     # Scheduler, check runner, email alerts
    config.py     # Settings from environment / .env
    main.py       # FastAPI app entry
frontend/
  app/            # Next.js pages
  lib/api.ts      # API client + monitor type definitions
```

## License

MIT
