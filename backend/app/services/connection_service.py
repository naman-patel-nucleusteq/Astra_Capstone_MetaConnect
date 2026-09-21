"""Business logic for Snowflake connection operations."""

from app.connectors.snowflake_connector import SnowflakeConnector
from app.schemas.connection_schemas import (
    SnowflakeColumnRequest,
    SnowflakeConnection,
    SnowflakeDatabaseRequest,
    SnowflakeSchemaRequest,
    SnowflakeTableRequest,
)


def connector(connection, include_schema: bool = True) -> SnowflakeConnector:
    return SnowflakeConnector(
        username=connection.username,
        password=connection.password,
        account=connection.account,
        warehouse=connection.warehouse,
        database=connection.database,
        schema=connection.schema_name if include_schema else None,
        role=connection.role,
    )


def test_connection(connection: SnowflakeConnection):
    """
    Test a Snowflake connection
    """
    snowflake_connector = connector(connection)
    snowflake_connector.test_connection()
    return {"success": True, "message": "Snowflake connection successful"}


def get_databases(connection: SnowflakeDatabaseRequest):
    """
    get databases metadata response  
    """
    snowflake_connector = connector(connection, include_schema=False)
    return snowflake_connector.get_databases()


def get_schemas(connection: SnowflakeSchemaRequest):
    """
    get schemas metadata response  
    """
    snowflake_connector = connector(connection)
    return snowflake_connector.get_schemas()


def get_tables(connection: SnowflakeTableRequest):
    """
    get columns metadata response  
    """
    snowflake_connector =  connector(connection)
    return snowflake_connector.get_tables()


def get_columns(connection: SnowflakeColumnRequest):
    """
    get columns metadata response  
    """
    snowflake_connector = connector(connection)
    return snowflake_connector.get_columns(
        database=connection.database,
        schema=connection.schema_name,
        table=connection.table,
    )
