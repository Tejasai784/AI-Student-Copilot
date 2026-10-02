# ASIP V2.0 Production Deployment Guide

## 1. Quick Start with Docker Compose

The simplest way to run ASIP V2.0 in production with zero dependencies is using Docker Compose:

```bash
# 1. Clone repository
git clone https://github.com/Tejasai784/AI-Student-Copilot.git
cd AI-Student-Copilot

# 2. Configure environment
cp .env.example .env
# Edit .env to add your GEMINI_API_KEY and secure JWT_SECRET_KEY

# 3. Start services
docker compose up -d --build

# 4. Access Platform:
# - Modern React Studio App: http://localhost:8000/app
# - REST API Docs (Swagger):  http://localhost:8000/docs
# - Streamlit Fallback UI:   http://localhost:8501
```

---

## 2. Bare-Metal / Local Production Run

### 2.1 Prerequisites
- Python 3.10+ (Recommended Python 3.11 or 3.12)
- Node.js 18+ & npm

### 2.2 Setup Steps

```bash
# 1. Create and activate Python virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Run database migrations
alembic upgrade head

# 4. Build React frontend bundle
cd frontend
npm ci
npm run build
cd ..

# 5. Start unified FastAPI server (serves REST API + React SPA)
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## 3. Reverse Proxy Configuration (Nginx)

For production HTTPS and domain routing, place Nginx in front of ASIP:

```nginx
server {
    listen 80;
    server_name copilot.yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name copilot.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/copilot.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/copilot.yourdomain.com/privkey.pem;

    client_max_body_size 50M;

    # SSE streaming configuration (disables proxy buffering)
    location /api/v1/chat/stream {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Connection '';
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 600s;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # All API, Static Assets, and React App routes
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 4. Backup & Disaster Recovery

- **Database**: SQLite database stored at `data/ai_student_copilot.db`. Nightly snapshots can be taken via SQLite online backup API or `sqlite3 data/ai_student_copilot.db ".backup 'backup_$(date +%F).db'"` without stopping the server (safe with WAL mode).
- **Uploaded Materials**: Store files in `data/uploads/`. Sync to secure S3/GCS bucket or persistent network volume.
- **Rollback Procedure**: To revert to any past migration revision:
  ```bash
  alembic downgrade -1
  ```
