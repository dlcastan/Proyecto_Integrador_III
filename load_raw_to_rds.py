import os, io, sys, datetime as dt
import boto3, pandas as pd, psycopg2

BUCKET = os.getenv("S3_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
LOCAL_FILE = "/app/data/AB_NYC.csv"
S3_PREFIX = os.getenv("S3_PREFIX", "raw/ab_nyc")

PGHOST=os.getenv("PGHOST"); PGDATABASE=os.getenv("PGDATABASE")
PGUSER=os.getenv("PGUSER"); PGPASSWORD=os.getenv("PGPASSWORD")
PGPORT=int(os.getenv("PGPORT","5432"))

TABLE_NAME = os.getenv("RAW_TABLE","ab_nyc_raw")

def upload_to_s3(path_local, bucket, key):
    s3 = boto3.client("s3", region_name=AWS_REGION)
    s3.upload_file(path_local, bucket, key)
    print(f"[RAW] Subido a s3://{bucket}/{key}")

def ensure_table(conn):
    cur = conn.cursor()
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            id BIGINT,
            name TEXT,
            host_id BIGINT,
            host_name TEXT,
            neighbourhood_group TEXT,
            neighbourhood TEXT,
            latitude DOUBLE PRECISION,
            longitude DOUBLE PRECISION,
            room_type TEXT,
            price INTEGER,
            minimum_nights INTEGER,
            number_of_reviews INTEGER,
            last_review DATE,
            reviews_per_month DOUBLE PRECISION,
            calculated_host_listings_count INTEGER,
            availability_365 INTEGER
        );
    """)
    conn.commit()
    cur.close()

def copy_df(conn, df: pd.DataFrame):
    df = df.copy()
    if "last_review" in df.columns:
        df["last_review"] = pd.to_datetime(df["last_review"], errors="coerce").dt.date

    buf = io.StringIO()
    df.to_csv(buf, index=False, header=False)
    buf.seek(0)
    cur = conn.cursor()
    cur.execute(f"TRUNCATE {TABLE_NAME};")
    cur.copy_expert(
        f"COPY {TABLE_NAME} FROM STDIN WITH CSV",
        buf
    )
    conn.commit()
    cur.close()
    print(f"[RAW] Cargadas {len(df):,} filas en {TABLE_NAME}")

def main():
    if not BUCKET:
        print("[RAW][ERROR] S3_BUCKET_NAME no definido", file=sys.stderr); sys.exit(1)
    if not os.path.exists(LOCAL_FILE):
        print(f"[RAW][ERROR] No existe {LOCAL_FILE}", file=sys.stderr); sys.exit(1)

    # 1) Subida a S3 con partición por fecha
    date_part = dt.datetime.utcnow().strftime("%Y-%m-%d")
    key = f"{S3_PREFIX}/ingest_date={date_part}/part-000.csv"
    upload_to_s3(LOCAL_FILE, BUCKET, key)

    # 2) Carga a RDS
    conn = psycopg2.connect(
        host=PGHOST, dbname=PGDATABASE, user=PGUSER, password=PGPASSWORD, port=PGPORT, 
        connect_timeout=60
    )
    ensure_table(conn)
    df = pd.read_csv(LOCAL_FILE)
    copy_df(conn, df)
    conn.close()

if __name__ == "__main__":
    main()
