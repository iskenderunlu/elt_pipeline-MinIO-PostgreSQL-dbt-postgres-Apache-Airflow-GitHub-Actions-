"""
ELT Pipeline DAG

Flow:
  extract_to_minio  →  load_to_dwh  →  dbt_run  →  dbt_test

Timing: every midnight (UTC)
Retry: each tak 2 times, in a period of 5 minutes
"""

from __future__ import annotations

import sys
import logging
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago

log = logging.getLogger(__name__)

# The Extract modules in airflow container in this path
sys.path.insert(0, "/opt/airflow/extract")

# ── Default task arguments ─────────────────────────────────────────────
default_args = {
    "owner":            "data-team",
    "depends_on_past":  False,
    "retries":          2,
    "retry_delay":      timedelta(minutes=5),
    "email_on_failure": False,   # gerçek projede True yapılır
}

# ── DAG Definition ──────────────────────────────────────────────────────────────
with DAG(
    dag_id="elt_pipeline",
    description="MinIO → PostgreSQL DWH → dbt transform",
    schedule_interval="0 0 * * *",   # her gün 00:00 UTC
    start_date=days_ago(1),
    default_args=default_args,
    catchup=False,
    tags=["elt", "dbt", "minio", "postgres"],
) as dag:

    # ── Task 1: Extract — generate data and upload onto MinIO ───────────────────────
    def _extract(**context):
        from generate_and_upload import run
        execution_date = context["execution_date"]
        result = run(execution_date=execution_date)
        log.info(f"Extract sonucu: {result}")
        # XCom'a yaz — bir sonraki task okuyabilir
        return result

    extract_task = PythonOperator(
        task_id="extract_to_minio",
        python_callable=_extract,
    )

    # ── Task 2: Load — Copy from MinIO to DWH ─────────────────────────────
    def _load(**context):
        from load_to_dwh import run
        execution_date = context["execution_date"]
        run(execution_date=execution_date)

    load_task = PythonOperator(
        task_id="load_to_dwh",
        python_callable=_load,
    )

    # ── Task 3: dbt run — it creates staging + mart models ────────────────
    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=(
            "cd /opt/airflow/dbt/elt_project && "
            "dbt run --profiles-dir /opt/airflow/dbt"
        ),
    )

    # ── Task 4: dbt test — Data quality control ───────────────────────────
    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=(
            "cd /opt/airflow/dbt/elt_project && "
            "dbt test --profiles-dir /opt/airflow/dbt"
        ),
    )

    # ── Task 5: dbt docs — creates lineage graph (optional) ─────────────
    dbt_docs = BashOperator(
        task_id="dbt_docs_generate",
        bash_command=(
            "cd /opt/airflow/dbt/elt_project && "
            "dbt docs generate --profiles-dir /opt/airflow/dbt"
        ),
        trigger_rule="all_success",
    )

    # ── Dependency Chain ───────────────────────────────────────────────────
    extract_task >> load_task >> dbt_run >> dbt_test >> dbt_docs
