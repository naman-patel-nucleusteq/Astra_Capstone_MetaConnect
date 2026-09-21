from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


def reject_numeric_only(value: str):
    if not any(character.isalpha() for character in value):
        raise ValueError("Pipeline name must contain at least one letter")
    return value


class PipelineCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=250, description="DAG / pipeline name")
    database_name: str | None = None
    schema_name: str | None = None
    schedule_type: str = Field(default="MANUAL", pattern="^(MANUAL|SCHEDULE)$")
    schedule: str | None = Field(default=None, max_length=120)

    validate_name = field_validator("name")(reject_numeric_only)


class PipelineUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=250)
    database_name: str | None = None
    schema_name: str | None = None
    schedule_type: str = Field(default="MANUAL", pattern="^(MANUAL|SCHEDULE)$")
    schedule: str | None = Field(default=None, max_length=120)

    validate_name = field_validator("name")(reject_numeric_only)


class PipelineResponse(BaseModel):
    id: UUID
    service_uuid: UUID | None = None
    name: str
    airflow_dag_id: str
    database_name: str | None = None
    schema_name: str | None = None
    schedule_type: str = "MANUAL"
    schedule: str | None = None
    status: str
    last_run_status: str | None = None
    last_ingestion_at: datetime | None = None
    created_by: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
