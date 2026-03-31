# ── Build stage ──────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Install dependencies into a prefix for easy copy
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Runtime stage ─────────────────────────────────────────────────
FROM python:3.11-slim

LABEL org.opencontainers.image.title="AI Team Platform" \
      org.opencontainers.image.description="Multi-agent collaboration platform powered by OpenClaw" \
      org.opencontainers.image.source="https://github.com/teng00123/ai_team_platform" \
      org.opencontainers.image.licenses="MIT"

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY main.py models.py team_manager.py cli.py ./
COPY static/ ./static/

# Init data directory with empty dicts
RUN mkdir -p data && echo "{}" > data/roles.json && echo "{}" > data/tasks.json

# Non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8765/health')"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8765"]
