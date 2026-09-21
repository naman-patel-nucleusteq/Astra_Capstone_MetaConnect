import time
import requests
from app.core.config import AIRFLOW_API_URL, AIRFLOW_USERNAME, AIRFLOW_PASSWORD


def request(method, path, **kwargs):
    url = f"{AIRFLOW_API_URL}{path}"
    response = requests.request(
        method,
        url,
        auth=(AIRFLOW_USERNAME, AIRFLOW_PASSWORD),
        timeout=30,
        **kwargs,
    )
    return response


def dag_exists(dag_id: str) -> bool:
    response = request("GET", f"/api/v1/dags/{dag_id}")
    return response.status_code == 200


def unpause_dag(dag_id: str):
    response = request("PATCH", f"/api/v1/dags/{dag_id}", json={"is_paused": False})
    if response.status_code not in (200, 201):
        raise RuntimeError(f"Failed to unpause Airflow DAG '{dag_id}': {response.status_code} - {response.text}")


def delete_dag(dag_id: str):
    response = request("DELETE", f"/api/v1/dags/{dag_id}")
    if response.status_code not in (200, 204, 404):
        raise RuntimeError(f"Failed to delete Airflow DAG '{dag_id}': {response.status_code} - {response.text}")


def wait_for_dag(dag_id: str, attempts: int = 12, delay_seconds: float = 5):
    last_error = None
    for _ in range(attempts):
        try:
            if dag_exists(dag_id):
                unpause_dag(dag_id)
                return
        except Exception as exc:
            last_error = exc
        time.sleep(delay_seconds)
    detail = f" Airflow error: {last_error}" if last_error else ""
    raise RuntimeError(
        f"Airflow DAG '{dag_id}' is not registered yet. Wait for the scheduler to parse pipelines and try again.{detail}"
    )


def trigger_dag(dag_id: str, conf: dict | None = None):
    wait_for_dag(dag_id)
    response = request("POST", f"/api/v1/dags/{dag_id}/dagRuns", json={"conf": conf or {}})
    if response.status_code not in (200, 201):
        raise RuntimeError(f"Failed to trigger Airflow DAG '{dag_id}': {response.status_code} - {response.text}")
    return response.json()


def trigger_metadata_ingestion(service_id: int):
    """
    Legacy helper kept for compatibility. Prefer trigger_dag() with a pipeline DAG ID.
    """
    return trigger_dag("metaconnect_metadata_ingestion", {"service_id": service_id})
