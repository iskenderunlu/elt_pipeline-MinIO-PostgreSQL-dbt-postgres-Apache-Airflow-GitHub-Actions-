# Cloud-Native ELT Pipeline (Local / Free Stack)

Tamamen ücretsiz, Docker tabanlı modern ELT pipeline.  
AWS ve Snowflake **gerektirmez** — açık kaynak alternatifleri kullanır.

## Mimari

```
[Veri Üretici]  →  [MinIO / S3]  →  [PostgreSQL DWH]  →  [dbt]  →  [Analitik]
     Python           raw/              raw schema         staging      marts
                    parquet            + watermark         + tests
                                                             ↑
                                                         [Airflow]
                                                          scheduler
```

| Araç | Üretim karşılığı | Açıklama |
|------|-------------------|---------|
| MinIO | AWS S3 | S3 uyumlu obje depolama, aynı boto3 kodu çalışır |
| PostgreSQL | Snowflake / Redshift | Data warehouse |
| dbt-postgres | dbt-snowflake | Aynı dbt, connector farklı |
| Airflow | AWS MWAA / GCP Composer | Orchestration |
| GitHub Actions | Aynı | CI/CD |

## Sonuçlar (CV için)

- Günlük ~50K satır veriyi MinIO → PostgreSQL'e **< 30 saniyede** yükler
- dbt ile **9 otomatik test** (unique, not_null, accepted_values, custom)
- CI/CD: her PR'da dbt compile + test + docs generate (~2 dk)
- Airflow retry mekanizması ile hata dayanıklılığı

## Kurulum

### Ön koşullar
- Docker Desktop (veya Docker Engine + Compose)
- Git
- 4 GB RAM (Airflow için)

### 1. Projeyi klonla

```bash
git clone https://github.com/KULLANICI_ADIN/elt-pipeline-local.git
cd elt-pipeline-local
```

### 2. Airflow için gerekli dizinleri oluştur

```bash
mkdir -p logs
echo "AIRFLOW_UID=$(id -u)" > .env   # Linux/Mac
# Windows PowerShell: "AIRFLOW_UID=50000" | Out-File -Encoding ascii .env
```

### 3. Servisleri başlat

```bash
# İlk başlatma (airflow-init tamamlanana kadar bekle ~2-3 dk)
docker compose up airflow-init

# Arka planda çalıştır
docker compose up -d
```

### 4. Servislerin ayakta olduğunu kontrol et

```bash
docker compose ps
```

Beklenen çıktı — hepsi `healthy` veya `running` olmalı:
```
NAME                  STATUS
airflow-webserver     running (healthy)
airflow-scheduler     running
minio                 running (healthy)
postgres-airflow      running (healthy)
postgres-dwh          running (healthy)
```

### 5. Arayüzlere bağlan

| Servis | URL | Kullanıcı | Şifre |
|--------|-----|-----------|-------|
| Airflow UI | http://localhost:8080 | admin | admin |
| MinIO UI | http://localhost:9001 | minioadmin | minioadmin |
| PostgreSQL DWH | localhost:5433 | dwh | dwh |

### 6. Pipeline'ı manuel çalıştır

Airflow UI → DAGs → `elt_pipeline` → Trigger DAG ▶

Veya komut satırından:
```bash
docker compose exec airflow-scheduler \
  airflow dags trigger elt_pipeline
```

### 7. Sonuçları kontrol et

```bash
# DWH'ye bağlan ve sorgula
psql postgresql://dwh:dwh@localhost:5433/dwh

-- Ham veri
SELECT COUNT(*) FROM raw.orders;

-- Staging (dbt view)
SELECT * FROM staging.stg_orders LIMIT 5;

-- Mart (analitik tablo)
SELECT product_category, SUM(revenue) as total_revenue
FROM marts.fct_orders
GROUP BY 1
ORDER BY 2 DESC;

-- Müşteri segmentleri
SELECT customer_segment, COUNT(*), AVG(total_spent_usd)
FROM marts.dim_customers
GROUP BY 1;
```

## Proje yapısı

```
elt_pipeline/
├── docker-compose.yml          ← tüm servisler burada
├── dags/
│   └── elt_pipeline_dag.py     ← Airflow DAG (4 task)
├── extract/
│   ├── generate_and_upload.py  ← Extract: veri üret → MinIO
│   └── load_to_dwh.py          ← Load: MinIO → PostgreSQL
├── dbt/
│   ├── profiles.yml            ← PostgreSQL bağlantısı
│   └── elt_project/
│       ├── dbt_project.yml
│       ├── models/
│       │   ├── staging/        ← raw → temizlenmiş view'lar
│       │   │   ├── sources.yml
│       │   │   ├── schema.yml  ← 6 otomatik test
│       │   │   ├── stg_orders.sql
│       │   │   ├── stg_customers.sql
│       │   │   └── stg_products.sql
│       │   └── marts/          ← analitik tablolar
│       │       ├── schema.yml  ← 3 otomatik test
│       │       ├── fct_orders.sql
│       │       └── dim_customers.sql
│       ├── tests/
│       │   └── assert_no_future_orders.sql  ← özel test
│       └── macros/
│           └── cents_to_dollars.sql
├── scripts/
│   └── init_dwh.sql            ← DWH şema oluşturma
└── .github/
    └── workflows/
        └── dbt_ci.yml          ← PR'da otomatik test
```

## dbt lineage

```
raw.orders ──────┐
                 ├── stg_orders ──────┐
raw.customers ───┤                    ├── fct_orders
                 ├── stg_customers ───┤
raw.products ────┘   └─ dim_customers └── dim_customers
                     stg_products ───┘
```

## Durdurma

```bash
docker compose down          # servisleri durdur, volume'ları koru
docker compose down -v       # her şeyi sil (temiz başlangıç)
```

## Sorun giderme

**Airflow başlamıyor:** `docker compose logs airflow-init` ile log'a bak.  
**dbt bağlanmıyor:** `docker compose exec airflow-scheduler dbt debug --profiles-dir /opt/airflow/dbt` çalıştır.  
**MinIO bucket yok:** `docker compose restart minio-init` ile bucket'ları yeniden oluştur.
# elt_pipeline-MinIO-PostgreSQL-dbt-postgres-Apache-Airflow-GitHub-Actions-
