# Deployment Guide

How to deploy the Codebook Monitoring Tool for development and production.

## Architecture

| Component | Technology | Default port |
|-----------|------------|--------------|
| Frontend  | Next.js 15 | `3000` |
| Backend   | FastAPI + Uvicorn + APScheduler | `8000` |
| Storage   | SQLite (`backend/monitoring.db`) | — |

The frontend proxies `/api/*` to the backend via a Next.js rewrite:

```js
// frontend/next.config.js
destination: "http://127.0.0.1:8000/api/:path*"
```

Browsers call the frontend only. The Next.js server forwards API requests to Uvicorn on the same host. Keep backend and frontend on one machine unless you change that rewrite.

```
Browser → :3000 (Next.js) → /api/* rewrite → :8000 (FastAPI) → monitoring.db
```

---

## Prerequisites

| Requirement | Version / notes |
|-------------|-----------------|
| Python | 3.10+ recommended |
| Node.js | 18+ (LTS) |
| npm | Comes with Node.js |
| Network | Outbound access to targets you monitor (HTTP, DB, TCP) |
| Linux only | `journalctl` / `systemctl` for systemd monitors |
| Oracle (optional) | Instant Client if connecting to Oracle 11g / thick mode |

---

## 1. Clone and configure

```bash
cd codebook-monitoring-tool
```

### Backend environment

```bash
cd backend
copy .env.example .env    # Windows
# cp .env.example .env    # Linux/macOS
```

Edit `backend/.env` as needed:

| Variable | Purpose | Default / example |
|----------|---------|-------------------|
| `ALERT_ENABLED` | Enable email alerts | `false` / `true` |
| `ALERT_TO` | Recipients (comma-separated) | `ops@example.com` |
| `ALERT_FROM` | From address | `monitoring@example.com` |
| `ALERT_ON_RECOVERY` | Email when service recovers | `true` |
| `ALERT_COOLDOWN_SECONDS` | Min seconds between repeat down alerts | `300` |
| `SMTP_HOST` / `SMTP_PORT` | SMTP server | e.g. `smtp.gmail.com` / `587` |
| `SMTP_USER` / `SMTP_PASSWORD` | SMTP auth | App password for Gmail |
| `SMTP_USE_TLS` | STARTTLS (port 587) | `true` |
| `SMTP_USE_SSL` | Implicit SSL (port 465) | `false` |
| `ORACLE_CLIENT_LIB_DIR` | Path to Instant Client (oci.dll / lib) | empty = thin mode |

Do not commit `.env`. It is gitignored.

---

## 2. Backend setup

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate

pip install -r requirements.txt
```

Drivers already listed in `requirements.txt`: `psycopg2-binary`, `pymysql`, `oracledb`.

### Run (development)

Always start Uvicorn from the `backend` directory so `monitoring.db` is created next to the app:

```bash
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- API: http://127.0.0.1:8000  
- OpenAPI docs: http://127.0.0.1:8000/docs  

### Run (production)

```bash
cd backend
# activate venv first
uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Use **one worker**. The in-process APScheduler and SQLite are not safe with multiple Uvicorn workers.

Bind to `127.0.0.1` when a reverse proxy or Next.js sits in front. Use `--host 0.0.0.0` only if the API must be reachable directly on the network.

---

## 3. Frontend setup

```bash
cd frontend
npm install
```

### Development

```bash
npm run dev
```

Open http://localhost:3000.

### Production build

```bash
npm run build
npm start
```

`npm start` serves on port 3000 by default. To change the port:

```bash
# Linux/macOS
PORT=8080 npm start

# Windows (PowerShell)
$env:PORT=8080; npm start
```

If the backend is not on `127.0.0.1:8000`, update `frontend/next.config.js` rewrites before building, then rebuild.

---

## 4. Quick start (Windows)

From the repo root:

```bat
start.bat
```

This opens two terminals: backend on `:8000` and frontend (`npm run dev`) on `:3000`. Prefer the production commands above for a permanent host.

---

## 5. Production layouts

### Option A — Same host (recommended)

1. Run FastAPI on `127.0.0.1:8000`
2. Run Next.js on `0.0.0.0:3000` (or behind a reverse proxy)
3. Leave the default rewrite pointing at `127.0.0.1:8000`

Users only need access to the frontend port (or to nginx/Caddy on 80/443).

### Option B — Reverse proxy (nginx example)

Terminate TLS and forward to Next.js. API traffic still goes Browser → Next → FastAPI via rewrite.

```nginx
server {
    listen 443 ssl;
    server_name monitoring.example.com;

    # ssl_certificate     /path/to/fullchain.pem;
    # ssl_certificate_key /path/to/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### CORS note

Backend CORS currently allows `http://localhost:3000` and `:3001` only. That is enough when the browser talks only to Next.js (same origin) and Next rewrites to the API. If you call the FastAPI origin directly from another domain, update `allow_origins` in `backend/app/main.py`.

---

## 6. Run as a service

### Linux — systemd

**Backend** — `/etc/systemd/system/codebook-backend.service`:

```ini
[Unit]
Description=Codebook Monitoring API
After=network.target

[Service]
Type=simple
User=monitoring
WorkingDirectory=/opt/codebook-monitoring-tool/backend
Environment=PATH=/opt/codebook-monitoring-tool/backend/venv/bin
ExecStart=/opt/codebook-monitoring-tool/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**Frontend** — `/etc/systemd/system/codebook-frontend.service`:

```ini
[Unit]
Description=Codebook Monitoring UI
After=network.target codebook-backend.service

[Service]
Type=simple
User=monitoring
WorkingDirectory=/opt/codebook-monitoring-tool/frontend
Environment=NODE_ENV=production
Environment=PORT=3000
ExecStart=/usr/bin/npm start
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now codebook-backend codebook-frontend
sudo systemctl status codebook-backend codebook-frontend
```

Adjust paths, user, and Node/npm location for your host.

### Windows — Task Scheduler or NSSM

1. Create a dedicated user or run under a service account with network access to monitored hosts.
2. Backend task (start in `backend` with venv activated), for example:

   ```bat
   cd /d C:\apps\codebook-monitoring-tool\backend
   call venv\Scripts\activate
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
   ```

3. Frontend task:

   ```bat
   cd /d C:\apps\codebook-monitoring-tool\frontend
   npm start
   ```

4. Set both to start at logon or as a service (e.g. [NSSM](https://nssm.cc/)).

---

## 7. Oracle Instant Client (optional)

Needed for Oracle **11g** and other cases that require thick mode.

1. Download Instant Client Basic for your OS from Oracle.
2. Unpack to a stable path (example Windows: `C:\oracle\instantclient_23_26`).
3. Set in `backend/.env`:

   ```env
   ORACLE_CLIENT_LIB_DIR=C:\oracle\instantclient_23_26
   ```

4. Restart the backend. Logs should show Oracle client mode (thick vs thin).

On Linux, ensure the Instant Client libraries are findable (`ldconfig` or `LD_LIBRARY_PATH`) in addition to `ORACLE_CLIENT_LIB_DIR`.

---

## 8. Data and backups

| Item | Location |
|------|----------|
| Monitor definitions & check history | `backend/monitoring.db` |
| Alert / SMTP config | `backend/.env` |

Backup:

```bash
# Stop backend briefly for a consistent copy, or use sqlite3 .backup
cp backend/monitoring.db /backup/monitoring-$(date +%Y%m%d).db
```

Restore by stopping the backend, replacing `monitoring.db`, and starting again. Create tables automatically on startup if the file is missing.

---

## 9. Firewall and security checklist

- [ ] Expose only the frontend (or reverse proxy) publicly; keep Uvicorn on localhost when possible.
- [ ] Use HTTPS in production (nginx/Caddy + certificates).
- [ ] Protect `.env` and `monitoring.db` (file permissions; never commit secrets).
- [ ] Restrict who can reach the UI (VPN, IP allowlist, or auth in front of the app — the app has no built-in login).
- [ ] Ensure the process user can reach monitored endpoints and, on Linux, read relevant journals for systemd monitors.
- [ ] Use SMTP app passwords / secrets management for alert credentials.

---

## 10. Verify deployment

1. Backend docs: http://127.0.0.1:8000/docs  
2. Frontend: http://localhost:3000 (or your public URL)  
3. Create an HTTP monitor (e.g. `https://example.com`) and run **Check Now**  
4. Confirm history updates and, if configured, a test down/up alert email  

---

## 11. Troubleshooting

| Symptom | What to check |
|---------|----------------|
| Frontend loads but API fails | Backend running? Started from `backend/`? Rewrite still `127.0.0.1:8000`? |
| `monitoring.db` missing / empty | Working directory must be `backend` when starting Uvicorn |
| Email not sent | `ALERT_ENABLED=true`, SMTP fields, firewall to SMTP port; check backend logs |
| Oracle connection fails | Service name/DSN, Instant Client path, thick mode for 11g |
| Systemd monitor fails | Linux host, `journalctl` in PATH, permissions for the unit |
| Multiple schedulers / odd checks | Ensure `--workers 1` |

---

## Related docs

- [README.md](./README.md) — features, monitor types, local quick start, email alert examples
