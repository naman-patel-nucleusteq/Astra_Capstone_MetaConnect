"""Airflow DAG"""

import logging
import sys
from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator

BACKEND_PATH = "/opt/airflow/backend"
if BACKEND_PATH not in sys.path:
    sys.path.insert(0, BACKEND_PATH)
SERVICES_PATH = "/opt/airflow/services"
if SERVICES_PATH not in sys.path:
    sys.path.insert(0, SERVICES_PATH)

from app.database.database import SessionLocal  
from app.database.models import Pipeline  
from metadata_ingestion_service import (  
    fetch_columns,
    fetch_databases,
    fetch_schemas,
    fetch_tables,
    load_and_test_connection,
    on_dag_failure,
    store_metadata,
    update_status,
)

log = logging.getLogger(__name__)


def create_pipeline_dag(dag_id: str, schedule=None) -> DAG:
    with DAG(
        dag_id=dag_id,
        start_date=datetime(2026, 1, 1),
        schedule=schedule,
        catchup=False,
        on_failure_callback=on_dag_failure,
        tags=["metaconnect", "metadata"],
    ) as dag:
        load_and_test = PythonOperator(
            task_id="load_and_test_connection",
            python_callable=load_and_test_connection,
        )
        databases = PythonOperator(
            task_id="fetch_databases",
            python_callable=fetch_databases,
        )
        schemas = PythonOperator(
            task_id="fetch_schemas",
            python_callable=fetch_schemas,
        )
        tables = PythonOperator(
            task_id="fetch_tables",
            python_callable=fetch_tables,
        )
        columns = PythonOperator(
            task_id="fetch_columns",
            python_callable=fetch_columns,
        )
        store = PythonOperator(
            task_id="store_metadata",
            python_callable=store_metadata,
        )
        status = PythonOperator(
            task_id="update_status",
            python_callable=update_status,
        )

        load_and_test >> databases >> schemas >> tables >> columns >> store >> status
    return dag


def load_pipeline_dags():
    try:
        db = SessionLocal()
        try:
            pipelines = db.query(Pipeline).all()
        finally:
            db.close()
    except Exception:
        log.exception("Unable to load MetaConnect pipelines for DAG generation")
        return

    for pipeline in pipelines:
        globals()[pipeline.airflow_dag_id] = create_pipeline_dag(
            pipeline.airflow_dag_id,
            pipeline.schedule if pipeline.schedule_type == "SCHEDULE" else None,
        )


load_pipeline_dags()
