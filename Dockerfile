# Scraper image: runs run_spiders.py on the schedule in docker/crontab.
# Builds for both the Raspberry Pi (arm64) and a normal PC (amd64).
FROM python:3.11-slim

# supercronic is a cron made for containers: it keeps the environment variables
# (database settings) and logs every run to the container output
ARG SUPERCRONIC_VERSION=v0.2.29

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Europe/Istanbul

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl tzdata \
    && curl -fsSL -o /usr/local/bin/supercronic \
       "https://github.com/aptible/supercronic/releases/download/${SUPERCRONIC_VERSION}/supercronic-linux-$(dpkg --print-architecture)" \
    && chmod +x /usr/local/bin/supercronic \
    && apt-get purge -y curl \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# installed before copying the code, so code changes do not reinstall every package
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["supercronic", "/app/docker/crontab"]
