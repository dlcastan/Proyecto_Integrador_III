#!/usr/bin/env bash
set -euo pipefail

: "${RUN_RAW:=true}"        # 1) Subir AB_NYC.csv a S3 y cargar a RDS
: "${RUN_BCRA_FETCH:=true}" # 2) Consultar API BCRA y guardar en S3
: "${RUN_DBT:=true}"        # 3) Correr dbt

if [ -f "/usr/local/share/ca-certificates/corporate-ca.crt" ]; then
  echo "[BOOT] Instalando CA corporativa…"
  update-ca-certificates || true
fi

if [ "${RUN_RAW}" = "true" ]; then
  echo "[RAW] Subiendo AB_NYC.csv a S3 y cargando en RDS…"
  python /app/scripts/load_raw_to_rds.py
fi

if [ "${RUN_BCRA_FETCH}" = "true" ]; then
  echo "[BCRA] Descargando series y subiendo a S3…"
  python /app/scripts/fetch_bcra.py
fi

if [ "${RUN_DBT}" = "true" ]; then
  echo "[DBT] deps…"
  dbt deps --project-dir /app/dbt
  echo "[DBT] debug…"
  dbt debug --project-dir /app/dbt
  echo "[DBT] build…"
  dbt build --project-dir /app/dbt
fi

echo "[DONE] Pipeline completo."
