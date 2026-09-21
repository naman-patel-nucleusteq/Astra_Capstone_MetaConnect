"""
Snowflake connection testing and metadata endpoints.
"""

from fastapi import APIRouter, Depends
from app.core.auth import get_current_user
from app.services import connection_service
from app.schemas.connection_schemas import (
    SnowflakeConnection,
    SnowflakeDatabaseRequest,
    SnowflakeSchemaRequest,
    SnowflakeTableRequest,
    SnowflakeColumnRequest,
)


router = APIRouter()


@router.post("/test")
def test_connection(connection: SnowflakeConnection, current_user: str = Depends(get_current_user),):
    """Test a Snowflake connection without saving any credentials."""

    return connection_service.test_connection(connection)



@router.post("/databases")
def get_databases(connection: SnowflakeDatabaseRequest, current_user: str = Depends(get_current_user),):
    """Return the list of databases visible to the given credentials."""

    return connection_service.get_databases(connection)


@router.post("/schemas")
def get_schemas(connection: SnowflakeSchemaRequest, current_user: str = Depends(get_current_user),):
    """Return schemas in the specified Snowflake database."""

    return connection_service.get_schemas(connection)


@router.post("/tables")
def get_tables(connection: SnowflakeTableRequest, current_user: str = Depends(get_current_user),):
    """Return tables in the specified Snowflake schema."""

    return connection_service.get_tables(connection)


@router.post("/columns")
def get_columns(connection: SnowflakeColumnRequest, current_user: str = Depends(get_current_user),):
    """Return columns for the specified Snowflake table."""

    return connection_service.get_columns(connection)
