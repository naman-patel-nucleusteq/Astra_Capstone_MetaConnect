from pydantic import BaseModel
from datetime import datetime
from typing import Any
from uuid import UUID


class IngestionRunResponse(BaseModel):
    id: int
    service_uuid: UUID | None = None
    pipeline_id: UUID | None = None
    status: str
    started_at: datetime
    finished_at: datetime | None = None
    error_message: str | None = None
    summary: dict[str, Any] | None = None
    created_by: str | None = None

    model_config = {"from_attributes": True}


class IngestionTriggerResponse(BaseModel):
    success: bool
    message: str
    airflow_dag_run: dict[str, Any] | None = None
