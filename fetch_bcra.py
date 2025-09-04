#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Descarga series monetarias del BCRA (API v3.0) y sube CSV/JSON a S3.

Config por variables de entorno:
- S3_BUCKET_NAME            (obligatorio)
- AWS_REGION                (default: us-east-1)
- VERIFY_SSL                (true/false; default: true)

- BCRA_BASE_URL             (default: https://api.bcra.gob.ar)
- BCRA_API_PATH             (default: /estadisticas/v3.0)
- BCRA_CAT_PATH             (default: /Monetarias)
- BCRA_SERIES               (coma-separado; alias o idVariable, ej: "usd_oficial,4")
- BCRA_FROM                 (YYYY-MM-DD; default: 1/ene del año en curso)
- BCRA_TO                   (YYYY-MM-DD; default: hoy)
- S3_BCRA_PREFIX            (default: raw/bcra)
"""

import os
import sys
import json
import re
import unicodedata
from datetime import date, datetime
from typing import List, Dict, Any

import boto3
import pandas as pd
import requests

try:
    import urllib3
except Exception:
    urllib3 = None

# ---------- Config ----------
BUCKET = os.getenv("S3_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
VERIFY_SSL = os.getenv("VERIFY_SSL", "true").lower() == "true"

BASE_URL = os.getenv("BCRA_BASE_URL", "https://api.bcra.gob.ar")
API_PATH = os.getenv("BCRA_API_PATH", "/estadisticas/v3.0")
CAT_PATH = os.getenv("BCRA_CAT_PATH", "/Monetarias")

SERIES_RAW = os.getenv("BCRA_SERIES", "usd_oficial")
SERIES: List[str] = [s.strip() for s in SERIES_RAW.split(",") if s.strip()]

today = date.today()
DATE_FROM = os.getenv("BCRA_FROM", date(today.year, 1, 1).isoformat())
DATE_TO = os.getenv("BCRA_TO", today.isoformat())

S3_PREFIX = os.getenv("S3_BCRA_PREFIX", "raw/bcra")

if not VERIFY_SSL and urllib3 is not None:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---------- Utils ----------
def log(msg: str) -> None:
    print(f"[BCRA] {msg}")

def http_json(url: str, params: Dict[str, Any] | None = None) -> Any:
    try:
        r = requests.get(url, params=params, timeout=30, verify=VERIFY_SSL)
        r.raise_for_status()
        return r.json()
    except requests.HTTPError as e:
        body = ""
        try:
            body = r.text[:300]
        except Exception:
            pass
        print(f"[BCRA][ERROR] {e} url={getattr(r,'url',url)} body={body}", file=sys.stderr)
        raise
    except Exception as e:
        print(f"[BCRA][ERROR] {e}", file=sys.stderr)
        raise

def slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()
    return s

# ---------- Catálogo (v3.0 /Monetarias) ----------
def load_catalog() -> pd.DataFrame:
    """Devuelve un DataFrame con al menos idVariable y descripcion."""
    url = f"{BASE_URL}{API_PATH}{CAT_PATH}"
    payload = http_json(url)
    data = payload.get("results", payload)
    df = pd.json_normalize(data)

    rename_map = {}
    if "idVariable" not in df.columns:
        for c in df.columns:
            if c.lower().endswith("idvariable"):
                rename_map[c] = "idVariable"
    if "descripcion" not in df.columns:
        for c in df.columns:
            if "descripcion" in c.lower() or "descripcion" in slug(c):
                rename_map[c] = "descripcion"
    if rename_map:
        df = df.rename(columns=rename_map)

    if not {"idVariable", "descripcion"}.issubset(set(df.columns)):
        raise RuntimeError("El catálogo no trae columnas esperadas (idVariable, descripcion).")
    return df[["idVariable", "descripcion"]].copy()

def resolve_id(alias_or_id: str, catalog: pd.DataFrame) -> int:
    """Si pasan un número, usa ese idVariable; si no, intenta casar por descripción."""
    if str(alias_or_id).isdigit():
        return int(alias_or_id)

    target = slug(alias_or_id.replace("_", " "))
    cat = catalog.copy()
    cat["desc_slug"] = cat["descripcion"].map(slug)
    tokens = target.split()
    score = cat["desc_slug"].apply(lambda d: sum(t in d for t in tokens))
    if score.max() == 0:
        raise RuntimeError(f"No se encontró idVariable para '{alias_or_id}'. Probá pasar el id numérico.")
    return int(cat.loc[score.idxmax(), "idVariable"])

# ---------- Datos de una serie (v3.0 /Monetarias/{id}) ----------
def fetch_series(id_var: int) -> pd.DataFrame:
    """Descarga todos los registros entre DATE_FROM y DATE_TO, con paginación (max 3000 por request)."""
    url = f"{BASE_URL}{API_PATH}{CAT_PATH}/{id_var}"
    limit_env = int(os.getenv("BCRA_LIMIT", "3000"))
    limit = min(limit_env, 3000)
    offset = 0
    frames: List[pd.DataFrame] = []

    while True:
        params = {
            "desde": f"{DATE_FROM}T00:00:00",
            "hasta": f"{DATE_TO}T23:59:59",
            "limit": limit,
            "offset": offset,
        }
        payload = http_json(url, params=params)
        rows = payload.get("results", payload)
        if not isinstance(rows, list) or len(rows) == 0:
            break
        df = pd.DataFrame(rows)
        frames.append(df)
        if len(rows) < limit:
            break
        offset += limit

    if not frames:
        return pd.DataFrame(columns=["idVariable", "valor", "fecha"])

    df = pd.concat(frames, ignore_index=True)
    c_fecha = "fecha" if "fecha" in df.columns else next((c for c in df.columns if "fecha" in slug(c)), None)
    c_valor = "valor" if "valor" in df.columns else next((c for c in df.columns if "valor" in slug(c) or "dato" in slug(c)), None)
    if not c_fecha or not c_valor:
        return pd.DataFrame(columns=["idVariable","valor","fecha"])

    df = df.rename(columns={c_fecha: "fecha", c_valor: "valor"})
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    df["idVariable"] = id_var
    df = df.dropna(subset=["fecha"])
    return df[["idVariable", "fecha", "valor"]].sort_values("fecha").reset_index(drop=True)

# ---------- S3 ----------
def upload_s3(obj_bytes: bytes, key: str, content_type: str) -> None:
    s3 = boto3.client("s3", region_name=AWS_REGION)
    s3.put_object(Bucket=BUCKET, Key=key, Body=obj_bytes, ContentType=content_type)
    log(f"Subido a s3://{BUCKET}/{key}")

# ---------- Main ----------
def main() -> None:
    if not BUCKET:
        print("[BCRA][ERROR] S3_BUCKET_NAME no definido", file=sys.stderr)
        sys.exit(1)

    log("Descargando series y subiendo a S3…")
    catalog = load_catalog()
    desc_by_id = {int(r.idVariable): r.descripcion for r in catalog.itertuples(index=False)}

    all_frames: List[pd.DataFrame] = []
    for serie in SERIES:
        try:
            idv = resolve_id(serie, catalog)
            df = fetch_series(idv)
            if df.empty:
                print(f"[BCRA][WARN] idVariable {idv}: 0 registros.")
            df["serie_alias"] = serie
            df["descripcion"] = desc_by_id.get(idv, None)
            all_frames.append(df)
        except Exception as e:
            print(f"[BCRA][ERROR] {serie}: {e}", file=sys.stderr)

    if all_frames:
        full = pd.concat(all_frames, ignore_index=True)
    else:
        full = pd.DataFrame(columns=["idVariable", "fecha", "valor", "serie_alias", "descripcion"])

    date_part = date.today().isoformat()
    csv_key = f"{S3_PREFIX}/ingest_date={date_part}/bcra_monetarias.csv"
    json_key = f"{S3_PREFIX}/ingest_date={date_part}/bcra_monetarias.json"

    upload_s3(full.to_csv(index=False).encode("utf-8"), csv_key, "text/csv")
    upload_s3(full.to_json(orient="records", date_format="iso").encode("utf-8"), json_key, "application/json")

    log(f"Series procesadas: {len(SERIES)} | Filas totales: {len(full):,}")

if __name__ == "__main__":
    main()
