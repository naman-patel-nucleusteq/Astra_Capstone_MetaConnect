"""
Catalog metadata read and search endpoints.
"""

from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.core.auth import get_current_user
from app.services import metadata_service
from app.schemas.metadata_schemas import (
    DatabaseResponse,
    SchemaResponse,
    TableResponse,
    ColumnResponse,
    SearchResult,
)


router = APIRouter()


# List all databases for a service
@router.get("/services/{service_uuid}/databases", response_model=list[DatabaseResponse])
def list_databases(service_uuid: UUID, db: Session = Depends(get_db), current_user: str = Depends(get_current_user),):
    """
    List all databases ingested for a service
    """

    return metadata_service.list_databases(service_uuid, db)


# List all schemas in a database
@router.get("/databases/{db_id}/schemas", response_model=list[SchemaResponse])
def list_schemas(db_id: int, db: Session = Depends(get_db),  current_user: str = Depends(get_current_user),):
    """
    List all schemas in a database
    """

    return metadata_service.list_schemas(db_id, db)


# List all tables in a schema
@router.get("/schemas/{schema_id}/tables", response_model=list[TableResponse])
def list_tables(schema_id: int, db: Session = Depends(get_db), current_user: str = Depends(get_current_user),):
    """
    List all tables in a schema
    """

    return metadata_service.list_tables(schema_id, db)


# List columns in a table
@router.get("/tables/{table_id}/columns", response_model=list[ColumnResponse])
def list_columns(table_id: int, db: Session = Depends(get_db), current_user: str = Depends(get_current_user),):
    """
    List all columns in a table, ordered by ordinal position
    """

    return metadata_service.list_columns(table_id, db)


# Full text search across catalog
@router.get("/search", response_model=list[SearchResult])
def search_catalog(
    q: str = Query(..., min_length=1, description="Search term"),
    type: str | None = Query(default=None, description="Filter by entity type: database, schema, table, column"),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """
    Search across the entire catalog by name or description.
    """
    return metadata_service.search_catalog(q, type, db)
