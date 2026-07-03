# ------- Build Stage -------
FROM python:3.12-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# ------- Runtime Stage -------
FROM python:3.12-slim

# FIX 1 & 2: Point PATH to appuser's home, and tell Python where to find the site-packages
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/home/appuser/.local/bin:$PATH \
    PYTHONPATH=/home/appuser/.local/lib/python3.12/site-packages

WORKDIR /app

RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    libpq5 \
    && apt-get purge -y --auto-remove perl-base ncurses-bin ncurses-base 2>/dev/null; \
    apt-get clean && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home appuser

# Switch to the non-root user BEFORE copying files so everything lands cleanly
USER appuser

# Your excellent permission fixes!
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local
COPY --chown=appuser:appuser . .

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "app:app"]
