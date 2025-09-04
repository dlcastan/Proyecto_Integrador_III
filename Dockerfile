# Dockerfile
FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    git ca-certificates \
 && update-ca-certificates \
 && rm -rf /var/lib/apt/lists/*

ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt


WORKDIR /app

RUN pip install --no-cache-dir \
    dbt-postgres==1.7.13 \
    pandas==2.2.2 \
    boto3==1.34.160 \
    psycopg2-binary==2.9.9 \
    requests==2.32.3 \
    certifi==2024.7.4

COPY dbt/ /app/dbt/
COPY scripts/ /app/scripts/
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh
RUN mkdir -p /app/data
COPY data/AB_NYC.csv /app/data/AB_NYC.csv

ENV DBT_PROFILES_DIR=/app/dbt
ENTRYPOINT ["/app/entrypoint.sh"]
