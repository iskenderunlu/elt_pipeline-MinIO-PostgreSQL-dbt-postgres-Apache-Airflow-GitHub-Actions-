# Cloud-Native ELT Pipeline (Local / Free Stack)

A fully free, Docker-based modern ELT pipeline.
No AWS or Snowflake account required — uses open-source alternatives.

## Architecture

```
[Data Generator]  →  [MinIO / S3]  →  [PostgreSQL DWH]  →  [dbt]  →  [Analytics]
     Python             raw/              raw schema         staging      marts
                       parquet           + watermark         + tests
                                                               ↑
                                                           [Airflow]
                                                            scheduler
```

| Tool | Production equivalent | Description |
|------|-----------------------|-------------|
| MinIO | AWS S3 | S3-compatible object storage — same boto3 code works |
| PostgreSQL | Snowflake / Redshift | Data warehouse |
| dbt-postgres | dbt-snowflake | Same dbt, different connector |
| Airflow | AWS MWAA / GCP Composer | Orchestration |
| GitHub Actions | Same | CI/CD |

## Results (for your CV)

- Loads ~50K rows per day from MinIO → PostgreSQL in **< 30 seconds**
- **9 automated dbt tests** (unique, not_null, accepted_values, custom)
- CI/CD: automatic dbt compile + test + docs generate on every PR (~2 min)
- Fault tolerance via Airflow retry mechanism

## Setup

### Prerequisites
- Docker Desktop (or Docker Engine + Compose)
- Git
- 4 GB RAM (required by Airflow)

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/elt-pipeline-local.git
cd elt-pipeline-local
```

### 2. Create required directories for Airflow

```bash
mkdir -p logs
echo "AIRFLOW_UID=$(id -u)" > .env   # Linux/Mac
# Windows PowerShell: "AIRFLOW_UID=50000" | Out-File -Encoding ascii .env
```

### 3. Start the services

```bash
# First-time init (wait for airflow-init to complete ~2-3 min)
docker compose up airflow-init

# Run in the background
docker compose up -d
```

### 4. Verify all services are running

```bash
docker compose ps
```

Expected output — all services should be `healthy` or `running`:
```
NAME                  STATUS
airflow-webserver     running (healthy)
airflow-scheduler     running
minio                 running (healthy)
postgres-airflow      running (healthy)
postgres-dwh          running (healthy)
```

### 5. Access the UIs

| Service | URL | Username | Password |
|---------|-----|----------|----------|
| Airflow UI | http://localhost:8080 | admin | admin |
| MinIO UI | http://localhost:9001 | minioadmin | minioadmin |
| PostgreSQL DWH | localhost:5433 | dwh | dwh |

### 6. Trigger the pipeline manually

Airflow UI → DAGs → `elt_pipeline` → Trigger DAG ▶

Or from the command line:
```bash
docker compose exec airflow-scheduler \
  airflow dags trigger elt_pipeline
```

### 7. Query the results

```bash
# Connect to the DWH and run queries
psql postgresql://dwh:dwh@localhost:5433/dwh

-- Raw data
SELECT COUNT(*) FROM raw.orders;

-- Staging (dbt view)
SELECT * FROM staging.stg_orders LIMIT 5;

-- Mart (analytics table)
SELECT product_category, SUM(revenue) AS total_revenue
FROM marts.fct_orders
GROUP BY 1
ORDER BY 2 DESC;

-- Customer segments
SELECT customer_segment, COUNT(*), AVG(total_spent_usd)
FROM marts.dim_customers
GROUP BY 1;
```

## Project structure

```
elt_pipeline/
├── docker-compose.yml          ← all services defined here
├── dags/
│   └── elt_pipeline_dag.py     ← Airflow DAG (4 tasks)
├── extract/
│   ├── generate_and_upload.py  ← Extract: generate data → MinIO
│   └── load_to_dwh.py          ← Load: MinIO → PostgreSQL
├── dbt/
│   ├── profiles.yml            ← PostgreSQL connection
│   └── elt_project/
│       ├── dbt_project.yml
│       ├── models/
│       │   ├── staging/        ← raw → cleaned views
│       │   │   ├── sources.yml
│       │   │   ├── schema.yml  ← 6 automated tests
│       │   │   ├── stg_orders.sql
│       │   │   ├── stg_customers.sql
│       │   │   └── stg_products.sql
│       │   └── marts/          ← analytics tables
│       │       ├── schema.yml  ← 3 automated tests
│       │       ├── fct_orders.sql
│       │       └── dim_customers.sql
│       ├── tests/
│       │   └── assert_no_future_orders.sql  ← custom singular test
│       └── macros/
│           └── cents_to_dollars.sql
├── scripts/
│   └── init_dwh.sql            ← DWH schema initialisation
└── .github/
    └── workflows/
        └── dbt_ci.yml          ← automated tests on every PR
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

## Stopping the stack

```bash
docker compose down          # stop services, keep volumes
docker compose down -v       # remove everything (clean slate)
```

## Troubleshooting

**Airflow won't start:** Check logs with `docker compose logs airflow-init`.  
**dbt can't connect:** Run `docker compose exec airflow-scheduler dbt debug --profiles-dir /opt/airflow/dbt`.  
**MinIO bucket missing:** Recreate buckets with `docker compose restart minio-init`.
