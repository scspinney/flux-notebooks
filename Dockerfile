# flux-notebooks/Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Runtime dependencies for serving Dash + DataLad operations.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    git \
    git-annex \
    tini \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.runtime.txt /tmp/requirements.runtime.txt
RUN pip install --upgrade pip && \
    pip install -r /tmp/requirements.runtime.txt

COPY . /app

RUN useradd --create-home --uid 10001 appuser && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8050

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=5 \
    CMD curl -fsS http://127.0.0.1:8050/auth >/dev/null || exit 1

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["gunicorn", "--workers", "2", "--threads", "4", "--timeout", "120", "--bind", "0.0.0.0:8050", "app:server"]
