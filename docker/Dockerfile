# ============================================================================
# Multi-stage Dockerfile for FastAPI app and Celery workers
# ============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Builder — install Python deps and Playwright browsers
# ---------------------------------------------------------------------------
FROM python:3.13-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies using uv-style venv
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium browser + all OS-level dependencies
RUN playwright install chromium --with-deps

# ---------------------------------------------------------------------------
# Stage 2: Runtime
# ---------------------------------------------------------------------------
FROM python:3.13-slim AS runtime

WORKDIR /app

# Runtime system dependencies (Playwright Chromium needs these)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    # Playwright Chromium OS dependencies
    libnss3 \
    libnspr4 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libxss1 \
    libglib2.0-0 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy Playwright browser binaries from builder
COPY --from=builder /root/.cache/ms-playwright /root/.cache/ms-playwright

# Copy application code
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Create non-root user and fix ownership of Playwright cache
RUN useradd -m -u 1000 appuser \
    && chown -R appuser:appuser /app \
    && chown -R appuser:appuser /root/.cache/ms-playwright || true
USER appuser

# Ensure Playwright can find browsers (re-link for the appuser home)
ENV PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright

# Health check (API only)
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default: run migrations (non-fatal) then start FastAPI
CMD ["sh", "-c", "alembic upgrade head || echo 'Migration failed or already up to date, continuing...' && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2"]

