# ---- Build stage: install dependencies into a self-contained virtualenv ----
FROM python:3.12-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt


# ---- Final stage: minimal runtime image, no build tools, no root ----
FROM python:3.12-slim

# APPLY OS PATCHES HERE (Must run as root, before dropping privileges)
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

RUN groupadd -r appuser && useradd -r -g appuser -d /app appuser

WORKDIR /app

# Bring in only the installed packages, not the build toolchain
COPY --from=builder /opt/venv /opt/venv

COPY app.py .
COPY templates/ templates/

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Make sure the non-root user can actually read what it needs to run
RUN chown -R appuser:appuser /app

EXPOSE 8080

USER appuser

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/healthz')" || exit 1

# Run with Flask's built-in server, kept simple for this project
CMD ["python", "app.py"]