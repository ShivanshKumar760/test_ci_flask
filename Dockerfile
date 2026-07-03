# ------- Build Stage -------
FROM python:3.12-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Build deps only needed to compile psycopg2 — isolated to this stage,
# never makes it into the final runtime image
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first so Docker can cache this layer
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# ------- Runtime Stage -------
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOME=/home/appuser \
    PATH=/home/appuser/.local/bin:$PATH \
    PYTHONPATH=/home/appuser/.local/lib/python3.12/site-packages

WORKDIR /app

# Patch OS packages, install only the runtime lib psycopg2 needs (not gcc/libpq-dev),
# and attempt to strip perl/ncurses (may no-op if apt/dpkg holds them as protected —
# unfixed CVEs on these are handled via ignore-unfixed in CI, not here)
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    libpq5 \
    && apt-get purge -y --auto-remove perl-base ncurses-bin ncurses-base 2>/dev/null; \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Create non-root user and ensure /app is writable by them
# (WORKDIR is created as root before USER switches, so it needs an explicit chown)
RUN useradd --create-home appuser && \
    chown appuser:appuser /app

# Copy installed Python packages from the builder stage (chowned to appuser)
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local

# Copy app code (chowned to appuser)
COPY --chown=appuser:appuser . .

USER appuser

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "app:app"]
