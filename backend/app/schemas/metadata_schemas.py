"metadata response schemas"

from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class DatabaseResponse(BaseModel):
    id: int
    service_uuid: UUID
    name: str
    description: str | None = None
    tags: list[str] | None = None
    created_by: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SchemaResponse(BaseModel):
    id: int
    database_id: int
    name: str
    description: str | None = None
    tags: list[str] | None = None
    created_by: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TableResponse(BaseModel):
    id: int
    schema_id: int
    name: str
    description: str | None = None
    tags: list[str] | None = None
    created_by: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ColumnResponse(BaseModel):
    id: int
    table_id: int
    name: str
    data_type: str
    is_nullable: bool
    ordinal_position: int
    is_primary_key: bool
    description: str | None = None
    tags: list[str] | None = None
    created_by: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# Search
class SearchResult(BaseModel):
    type: str     
    id: int
    name: str
    description: str | None = None
    tags: list[str] | None = None
    parent: str | None = None 
    path: str | None = None
    service_name: str | None = None
    created_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    data_type: str | None = None
    is_nullable: bool | None = None
    ordinal_position: int | None = None
    is_primary_key: bool | None = None
