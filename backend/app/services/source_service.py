"""Business logic for registered source services and ingestion runs."""

from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.connectors.factory import get_connector_capabilities
from app.connectors.factory import get_connector
from app.core.encryption import decrypt_password, encrypt_password
from app.database.models import Database, IngestionRun, MetadataColumn, MetadataStaging, Pipeline, Schema, Service, Table
from app.integrations.airflow_client import delete_dag, trigger_dag
from app.schemas.ingestion_schemas import IngestionTriggerResponse
from app.schemas.service_schemas import ServiceConnectionTest, ServiceCreate, ServiceUpdate


def get_service(service_uuid: UUID, db: Session):
    service = db.query(Service).filter(Service.uuid == service_uuid).first()
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Service {service_uuid} not found")
    return service


def create_service(service: ServiceCreate, db: Session, current_user: str):
    airflow_connection_id = f"metaconnect_{service.service_type.lower()}_{service.name.lower().replace(' ', '_')}"
    new_service = Service(
        name=service.name,
        description=service.description,
        service_type=service.service_type,
        username=service.username,
        encrypted_password=encrypt_password(service.password),
        connection_details=service.connection_details,
        airflow_connection_id=airflow_connection_id,
        created_by=current_user,
    )
    db.add(new_service)
    db.commit()
    db.refresh(new_service)
    return new_service


def update_service(service_uuid: UUID, payload: ServiceUpdate, db: Session):
    service = get_service(service_uuid, db)
    duplicate = db.query(Service).filter(Service.name == payload.name.strip(), Service.id != service.id).first()
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A connection with this name already exists")
    service.name = payload.name.strip()
    service.description = payload.description
    if payload.username is not None:
        service.username = payload.username.strip()
    if payload.password:
        service.encrypted_password = encrypt_password(payload.password)
    if payload.connection_details is not None:
        service.connection_details = payload.connection_details
    db.commit()
    db.refresh(service)
    return service


def test_updated_service_connection(service_uuid: UUID, payload: ServiceConnectionTest, db: Session):
    service = get_service(service_uuid, db)
    details = {**(service.connection_details or {}), **(payload.connection_details or {})}
    username = payload.username.strip() if payload.username else service.username
    password = payload.password or decrypt_password(service.encrypted_password)
    if not username or not password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username and password are required to test this connection")
    try:
        connector = get_connector(
            service_type=service.service_type,
            username=username,
            password=password,
            connection_details=details,
        )
        connector.test_connection()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Connection test failed: {exc}") from exc
    return {"success": True, "message": f"{service.service_type} connection successful"}


def list_services(db: Session):
    return db.query(Service).order_by(Service.created_at.desc()).all()


def delete_service(service_uuid: UUID, db: Session):
    service = get_service(service_uuid, db)
    dag_ids = [pipeline.airflow_dag_id for pipeline in service.pipelines]
    run_ids = db.query(IngestionRun.id).filter(IngestionRun.service_id == service.id)
    db.query(MetadataStaging).filter(MetadataStaging.ingestion_run_id.in_(run_ids)).delete(synchronize_session=False)
    db.query(IngestionRun).filter(IngestionRun.service_id == service.id).delete(synchronize_session=False)
    db.query(Pipeline).filter(Pipeline.service_id == service.id).delete(synchronize_session=False)
    db.query(MetadataColumn).filter(
        MetadataColumn.table_id.in_(
            db.query(Table.id)
            .join(Schema, Table.schema_id == Schema.id)
            .join(Database, Schema.database_id == Database.id)
            .filter(Database.service_id == service.id)
        )
    ).delete(synchronize_session=False)
    db.query(Table).filter(
        Table.schema_id.in_(
            db.query(Schema.id)
            .join(Database, Schema.database_id == Database.id)
            .filter(Database.service_id == service.id)
        )
    ).delete(synchronize_session=False)
    db.query(Schema).filter(
        Schema.database_id.in_(db.query(Database.id).filter(Database.service_id == service.id))
    ).delete(synchronize_session=False)
    db.query(Database).filter(Database.service_id == service.id).delete(synchronize_session=False)
    db.delete(service)
    db.commit()
    for dag_id in dag_ids:
        try:
            delete_dag(dag_id)
        except RuntimeError:
            pass


def trigger_ingestion(service_uuid: UUID, db: Session):
    service = get_service(service_uuid, db)
    pipelines = db.query(Pipeline).filter(Pipeline.service_id == service.id).all()
    if not pipelines:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Create a pipeline for this connection before running ingestion.",
        )
    dag_runs = []
    try:
        for pipeline in pipelines:
            dag_runs.append(
                trigger_dag(
                    dag_id=pipeline.airflow_dag_id,
                    conf={"pipeline_id": str(pipeline.id), "service_id": service.id},
                )
            )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Failed to trigger Airflow DAG: {exc}")
    return IngestionTriggerResponse(
        success=True,
        message=f"Metadata ingestion triggered for {len(pipelines)} pipeline(s) on service '{service.name}'",
        airflow_dag_run=dag_runs[0] if len(dag_runs) == 1 else {"runs": dag_runs},
    )


def list_ingestion_runs(service_uuid: UUID, db: Session):
    service = get_service(service_uuid, db)
    return db.query(IngestionRun).filter(IngestionRun.service_id == service.id).order_by(IngestionRun.started_at.desc()).all()


def get_ingestion_run(service_uuid: UUID, run_id: int, db: Session):
    service = get_service(service_uuid, db)
    run = db.query(IngestionRun).filter(IngestionRun.id == run_id, IngestionRun.service_id == service.id).first()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"IngestionRun {run_id} not found for service {service_uuid}")
    return run


def service_capabilities(service: Service) -> dict[str, bool]:
    try:
        return get_connector_capabilities(service.service_type)
    except ValueError:
        return {
            "supports_databases": True,
            "supports_schemas": True,
            "supports_tables": True,
            "supports_columns": True,
        }
