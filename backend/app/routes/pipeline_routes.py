"""Pipeline CRUD and run endpoints."""

from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.auth import get_current_user
from app.database.database import get_db
from app.database.models import Service
from app.schemas.ingestion_schemas import IngestionRunResponse, IngestionTriggerResponse
from app.schemas.pipeline_schemas import PipelineCreate, PipelineResponse, PipelineUpdate
from app.services import pipeline_service

router = APIRouter()


def with_service_uuid(pipeline, db: Session) -> PipelineResponse:
    service = db.query(Service).filter(Service.id == pipeline.service_id).first()
    response = PipelineResponse.model_validate(pipeline)
    response.service_uuid = service.uuid if service else None
    latest_run = max(pipeline.ingestion_runs, key=lambda run: run.started_at) if pipeline.ingestion_runs else None
    response.last_run_status = latest_run.status if latest_run else None
    response.last_ingestion_at = latest_run.finished_at or latest_run.started_at if latest_run else None
    return response


@router.get("/services/{service_uuid}/pipelines", response_model=list[PipelineResponse])
def list_pipelines(
    service_uuid: UUID,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    return [with_service_uuid(pipeline, db) for pipeline in pipeline_service.get_all_pipelines(service_uuid, db)]


@router.post("/services/{service_uuid}/pipelines", response_model=PipelineResponse, status_code=status.HTTP_201_CREATED)
def create_pipeline(
    service_uuid: UUID,
    payload: PipelineCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    pipeline = pipeline_service.create_pipeline(service_uuid, payload, db, current_user)
    return with_service_uuid(pipeline, db)





@router.get("/pipelines/{pipeline_id}", response_model=PipelineResponse)
def get_pipeline(
    pipeline_id: UUID,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    return with_service_uuid(pipeline_service.get_pipeline(pipeline_id, db), db)


@router.put("/pipelines/{pipeline_id}", response_model=PipelineResponse)
def update_pipeline(
    pipeline_id: UUID,
    payload: PipelineUpdate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    return with_service_uuid(pipeline_service.update_pipeline(pipeline_id, payload, db), db)


@router.delete("/pipelines/{pipeline_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pipeline(
    pipeline_id: UUID,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    pipeline_service.delete_pipeline(pipeline_id, db)


@router.post("/pipelines/{pipeline_id}/run", response_model=IngestionTriggerResponse)
def run_pipeline(
    pipeline_id: UUID,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    return pipeline_service.trigger_pipeline(pipeline_id, db)


@router.get("/pipelines/{pipeline_id}/ingestion-runs", response_model=list[IngestionRunResponse])
def list_pipeline_runs(
    pipeline_id: UUID,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    return pipeline_service.list_pipeline_runs(pipeline_id, db)
