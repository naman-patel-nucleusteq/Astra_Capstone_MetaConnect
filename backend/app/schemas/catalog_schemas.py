from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class CatalogRunResponse(BaseModel):
    id: int
    service_uuid: UUID | None = None
    pipeline_id: str | None = None
    service_name: str
    name: str = "Metadata ingestion"
    dag_id: str | None = None
    status: str
    started_at: datetime
    finished_at: datetime | None = None
    error_message: str | None = None
    summary: dict[str, Any] | None = None


class CatalogOverviewResponse(BaseModel):
    services: int
    databases: int
    tables: int
    schemas: int
    runs: list[CatalogRunResponse]


class CatalogTreeResponse(BaseModel):
    services: list[dict[str, Any]]
