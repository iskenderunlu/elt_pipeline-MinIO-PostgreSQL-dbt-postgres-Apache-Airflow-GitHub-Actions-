"""
Extract layer — data generation and upload to MinIO.

In a real-world scenario, this script would read data from an API, database, or file system.

Here, we generate mock e-commerce data using pandas.

With each execution, only new records are added (simulating CDC — Change Data Capture).
"""

import os
import io
import json
import random
import logging
from datetime import datetime, timedelta

import boto3
import pandas as pd
from botocore.config import Config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Bağlantı ayarları (env'den okunur, docker-compose'da tanımlı) ──────────
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID", "minioadmin")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "minioadmin")
BUCKET          = os.getenv("MINIO_BUCKET", "elt-pipeline-raw")

# ── S3 client (MinIO uyumlu) ───────────────────────────────────────────────
def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


# ── Veri üretimi ────────────────────────────────────────────────────────────
CITIES    = ["Istanbul", "Ankara", "Izmir", "Bursa", "Antalya"]
COUNTRIES = ["TR"]
STATUSES  = ["PENDING", "SHIPPED", "DELIVERED", "CANCELLED"]
PRODUCTS  = [
    ("P001", "Laptop",     "Electronics",  12999.99),
    ("P002", "Mouse",      "Electronics",    249.90),
    ("P003", "Desk",       "Furniture",    3499.00),
    ("P004", "Headphones", "Electronics",    899.00),
    ("P005", "Notebook",   "Stationery",     29.90),
]

def generate_customers(n=200):
    rows = []
    for i in range(1, n + 1):
        rows.append({
            "customer_id":   f"C{i:04d}",
            "customer_name": f"Müşteri {i}",
            "email":         f"customer{i}@example.com",
            "city":          random.choice(CITIES),
            "country":       "TR",
            "signup_date":   (datetime(2023, 1, 1) + timedelta(days=random.randint(0, 365))).date().isoformat(),
        })
    return pd.DataFrame(rows)

def generate_products():
    return pd.DataFrame([
        {"product_id": p[0], "product_name": p[1], "category": p[2], "unit_price": p[3]}
        for p in PRODUCTS
    ])

def generate_orders(execution_date: datetime, n_per_day=50):
    """Her çalıştırmada o günün siparişlerini üretir (CDC simülasyonu)."""
    rows = []
    for i in range(n_per_day):
        product = random.choice(PRODUCTS)
        quantity = random.randint(1, 5)
        rows.append({
            "order_id":    f"O{execution_date.strftime('%Y%m%d')}{i:03d}",
            "customer_id": f"C{random.randint(1, 200):04d}",
            "order_date":  execution_date.date().isoformat(),
            "status":      random.choice(STATUSES),
            "amount":      round(product[3] * quantity, 2),
            "product_id":  product[0],
            "quantity":    quantity,
        })
    return pd.DataFrame(rows)


# ── S3 / MinIO yükleme ──────────────────────────────────────────────────────
def upload_parquet(s3, df: pd.DataFrame, key: str):
    """DataFrame'i bellekte parquet'e çevirir ve S3'e yükler (disk yok)."""
    buffer = io.BytesIO()
    df.to_parquet(buffer, index=False, engine="pyarrow")
    buffer.seek(0)
    s3.put_object(Bucket=BUCKET, Key=key, Body=buffer.getvalue())
    log.info(f"Uploaded {len(df):,} rows → s3://{BUCKET}/{key}")


def run(execution_date: datetime = None):
    if execution_date is None:
        execution_date = datetime.utcnow()

    dt = execution_date.strftime("%Y-%m-%d")
    log.info(f"Extract başlıyor — tarih: {dt}")

    s3 = get_s3_client()

    # 1. Customers — her zaman tam snapshot (küçük referans tablo)
    customers = generate_customers(200)
    upload_parquet(s3, customers, f"raw/customers/dt={dt}/customers.parquet")

    # 2. Products — her zaman tam snapshot
    products = generate_products()
    upload_parquet(s3, products, f"raw/products/dt={dt}/products.parquet")

    # 3. Orders — sadece o günün kayıtları (incremental / CDC)
    orders = generate_orders(execution_date, n_per_day=50)
    upload_parquet(s3, orders, f"raw/orders/dt={dt}/orders.parquet")

    log.info("Extract tamamlandı.")
    return {"date": dt, "orders": len(orders), "customers": len(customers)}


if __name__ == "__main__":
    # Manuel test: python generate_and_upload.py
    result = run()
    print(json.dumps(result, indent=2))
