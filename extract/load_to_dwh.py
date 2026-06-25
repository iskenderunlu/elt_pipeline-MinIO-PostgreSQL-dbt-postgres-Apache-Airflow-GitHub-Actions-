"""
Load katmanı — MinIO'daki parquet dosyalarını PostgreSQL DWH'ye yükler.

Strateji:
  - customers / products: TRUNCATE + INSERT (tam snapshot, küçük tablolar)
  - orders:               sadece o günün partition'ı INSERT (incremental)

Gerçek hayatta Snowflake'in COPY INTO komutu bu işi tek satırda yapardı.
PostgreSQL'de aynı şeyi psycopg2 + COPY FROM STDIN ile yapıyoruz.
"""

import os
import io
import logging
from datetime import datetime

import boto3
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from botocore.config import Config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Bağlantı ayarları ────────────────────────────────────────────────────────
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID", "minioadmin")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "minioadmin")
BUCKET         = os.getenv("MINIO_BUCKET", "elt-pipeline-raw")

DWH_HOST = os.getenv("DWH_HOST", "localhost")
DWH_PORT = int(os.getenv("DWH_PORT", "5433"))
DWH_DB   = os.getenv("DWH_DB", "dwh")
DWH_USER = os.getenv("DWH_USER", "dwh")
DWH_PASS = os.getenv("DWH_PASSWORD", "dwh")


def get_s3():
    return boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def get_conn():
    return psycopg2.connect(
        host=DWH_HOST, port=DWH_PORT, dbname=DWH_DB,
        user=DWH_USER, password=DWH_PASS,
    )


def read_parquet_from_s3(s3, key: str) -> pd.DataFrame:
    """S3'teki parquet dosyasını bellekte DataFrame'e çevirir."""
    obj = s3.get_object(Bucket=BUCKET, Key=key)
    return pd.read_parquet(io.BytesIO(obj["Body"].read()))


def bulk_insert(conn, df: pd.DataFrame, table: str, columns: list):
    """psycopg2 execute_values ile hızlı toplu insert."""
    rows = [tuple(row[c] for c in columns) for _, row in df.iterrows()]
    cols = ", ".join(columns)
    placeholders = "(" + ", ".join(["%s"] * len(columns)) + ")"
    sql = f"INSERT INTO {table} ({cols}) VALUES %s ON CONFLICT DO NOTHING"
    with conn.cursor() as cur:
        execute_values(cur, sql, rows)
    conn.commit()
    log.info(f"Inserted {len(rows):,} rows into {table}")


def load_customers(s3, conn, dt: str):
    key = f"raw/customers/dt={dt}/customers.parquet"
    df  = read_parquet_from_s3(s3, key)
    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE raw.customers")
    conn.commit()
    bulk_insert(conn, df, "raw.customers",
                ["customer_id", "customer_name", "email", "city", "country", "signup_date"])


def load_products(s3, conn, dt: str):
    key = f"raw/products/dt={dt}/products.parquet"
    df  = read_parquet_from_s3(s3, key)
    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE raw.products")
    conn.commit()
    bulk_insert(conn, df, "raw.products",
                ["product_id", "product_name", "category", "unit_price"])


def load_orders(s3, conn, dt: str):
    key = f"raw/orders/dt={dt}/orders.parquet"
    df  = read_parquet_from_s3(s3, key)
    # Order ID zaten partition-unique, ON CONFLICT DO NOTHING ile güvenli
    bulk_insert(conn, df, "raw.orders",
                ["order_id", "customer_id", "order_date", "status",
                 "amount", "product_id", "quantity"])

    # Watermark'ı güncelle
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO raw._load_watermarks (table_name, last_loaded_at)
            VALUES ('orders', NOW())
            ON CONFLICT (table_name) DO UPDATE SET last_loaded_at = NOW()
        """)
    conn.commit()


def run(execution_date: datetime = None):
    if execution_date is None:
        execution_date = datetime.utcnow()

    dt = execution_date.strftime("%Y-%m-%d")
    log.info(f"Load başlıyor — tarih: {dt}")

    s3   = get_s3()
    conn = get_conn()

    try:
        load_customers(s3, conn, dt)
        load_products(s3, conn, dt)
        load_orders(s3, conn, dt)
        log.info("Load tamamlandı.")
    finally:
        conn.close()


if __name__ == "__main__":
    run()
