FROM apache/airflow:2.10.3-python3.12

USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

USER airflow

COPY airflow/requirements.txt /requirements.txt

RUN pip install --no-cache-dir -r /requirements.txt

COPY airflow/dags /opt/airflow/dags
COPY airflow/services /opt/airflow/services
COPY backend /opt/airflow/backend

ENV PYTHONPATH=/opt/airflow/backend
