# syntax=docker/dockerfile:1
# Multi-stage production Dockerfile for Autonomous Student Intelligence Platform (ASIP V2.0)

# ==============================================================================
# Stage 1: Build Modern React Frontend
# ==============================================================================
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ==============================================================================
# Stage 2: Production Python Backend & Integrated Runtime
# ==============================================================================
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    APP_ENV=production \
    PORT=8000

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code & database migrations
COPY backend/ ./backend/
COPY database/ ./database/
COPY models/ ./models/
COPY rag/ ./rag/
COPY services/ ./services/
COPY tools/ ./tools/
COPY utils/ ./utils/
COPY memory/ ./memory/
COPY agents/ ./agents/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY app.py .
COPY ui/ ./ui/

# Copy built React frontend assets from Stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Create storage directories and set secure non-root permissions
RUN mkdir -p /app/data/uploads /app/data/vector_store && \
    useradd -u 1000 -m appuser && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/diagnostics/health || exit 1

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
