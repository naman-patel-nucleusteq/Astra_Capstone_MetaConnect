"""Business logic for metadata pipelines."""

import re
from datetime import datetime, timezone
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.connectors.factory import get_connector_capabilities
from app.database.models import IngestionRun, MetadataStaging, Pipeline, Service
from app.integrations.airflow_client import delete_dag, trigger_dag
from app.schemas.ingestion_schemas import IngestionTriggerResponse
from app.schemas.pipeline_schemas import PipelineCreate, PipelineUpdate

AIRFLOW_DAG_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


def now_utc():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def service_by_uuid(service_uuid: UUID, db: Session) -> Service:
    service = db.query(Service).filter(Service.uuid == service_uuid).first()
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Service {service_uuid} not found")
    return service


def get_pipeline_record(pipeline_id: UUID, db: Session) -> Pipeline:
    pipeline = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
    if not pipeline:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Pipeline {pipeline_id} not found")
    return pipeline


def validate_dag_id(dag_id: str):
    if not dag_id or not AIRFLOW_DAG_ID_PATTERN.match(dag_id) or len(dag_id) > 250:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="DAG name must be 1-250 characters and contain only letters, numbers, dots, dashes, and underscores.",
        )


def create_pipeline(service_uuid: UUID, payload: PipelineCreate, db: Session, current_user: str):
    service = service_by_uuid(service_uuid, db)
    if db.query(Pipeline).filter(Pipeline.service_id == service.id).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This connection already has a pipeline")
    dag_id = payload.name.strip()
    validate_dag_id(dag_id)

    existing = db.query(Pipeline).filter(Pipeline.airflow_dag_id == dag_id).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"DAG name '{dag_id}' is already in use")

    capabilities = get_connector_capabilities(service.service_type)
    schema_name = payload.schema_name.strip() if payload.schema_name else None
    if schema_name and not capabilities.get("supports_schemas"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{service.service_type} connectors do not support schema scope",
        )
    if payload.schedule_type == "SCHEDULE" and not payload.schedule:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A schedule is required when Schedule is selected")

    timestamp = now_utc()
    pipeline = Pipeline(
        service_id=service.id,
        name=dag_id,
        airflow_dag_id=dag_id,
        database_name=payload.database_name.strip() if payload.database_name else None,
        schema_name=schema_name,
        schedule_type=payload.schedule_type,
        schedule=payload.schedule.strip() if payload.schedule else None,
        status="READY",
        created_by=current_user,
        created_at=timestamp,
        updated_at=timestamp,
    )
    db.add(pipeline)
    db.commit()
    db.refresh(pipeline)
    return pipeline


def get_all_pipelines(service_uuid: UUID, db: Session):
    service = service_by_uuid(service_uuid, db)
    return db.query(Pipeline).filter(Pipeline.service_id == service.id).order_by(Pipeline.created_at.desc()).all()


def get_pipeline(pipeline_id: UUID, db: Session):
    return get_pipeline_record(pipeline_id, db)


def update_pipeline(pipeline_id: UUID, payload: PipelineUpdate, db: Session):
    pipeline = get_pipeline_record(pipeline_id, db)
    dag_id = payload.name.strip()
    validate_dag_id(dag_id)
    existing = db.query(Pipeline).filter(Pipeline.airflow_dag_id == dag_id, Pipeline.id != pipeline.id).first()

    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"DAG name '{dag_id}' is already in use")
    capabilities = get_connector_capabilities(pipeline.service.service_type)

    if payload.schema_name and not capabilities.get("supports_schemas"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{pipeline.service.service_type} connectors do not support schema scope")

    if payload.schedule_type == "SCHEDULE" and not payload.schedule:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A schedule is required when Schedule is selected")

    old_dag_id = pipeline.airflow_dag_id
    pipeline.name = dag_id
    pipeline.airflow_dag_id = dag_id
    pipeline.database_name = payload.database_name.strip() if payload.database_name else None
    pipeline.schema_name = payload.schema_name.strip() if payload.schema_name else None
    pipeline.schedule_type = payload.schedule_type
    pipeline.schedule = payload.schedule.strip() if payload.schedule else None
    pipeline.updated_at = now_utc()
    
    db.commit()
    db.refresh(pipeline)
    if old_dag_id != dag_id:
        try:
            delete_dag(old_dag_id)
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    return pipeline


def delete_pipeline(pipeline_id: UUID, db: Session):
    pipeline = get_pipeline_record(pipeline_id, db)
    dag_id = pipeline.airflow_dag_id
    run_ids = db.query(IngestionRun.id).filter(IngestionRun.pipeline_id == pipeline.id)
    db.query(MetadataStaging).filter(MetadataStaging.ingestion_run_id.in_(run_ids)).delete(synchronize_session=False)
    db.query(IngestionRun).filter(IngestionRun.pipeline_id == pipeline.id).delete(synchronize_session=False)
    db.delete(pipeline)
    db.commit()
    try:
        delete_dag(dag_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))


def trigger_pipeline(pipeline_id: UUID, db: Session):
    pipeline = get_pipeline_record(pipeline_id, db)
    try:
        dag_run = trigger_dag(
            dag_id=pipeline.airflow_dag_id,
            conf={"pipeline_id": str(pipeline.id), "service_id": pipeline.service_id},
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    pipeline.status = "RUNNING"
    pipeline.updated_at = now_utc()
    db.commit()
    db.refresh(pipeline)
    return IngestionTriggerResponse(
        success=True,
        message=f"Metadata ingestion triggered for pipeline '{pipeline.name}'",
        airflow_dag_run=dag_run,
    )


def list_pipeline_runs(pipeline_id: UUID, db: Session):
    pipeline = get_pipeline_record(pipeline_id, db)
    return (
        db.query(IngestionRun)
        .filter(IngestionRun.pipeline_id == pipeline.id)
        .order_by(IngestionRun.started_at.desc())
        .all()
    )
