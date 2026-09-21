from app.connectors.snowflake_connector import SnowflakeConnector


CONNECTOR_REGISTRY = {
    "SNOWFLAKE": SnowflakeConnector,
}


def connector_class(service_type: str):
    connector_class = CONNECTOR_REGISTRY.get((service_type or "").upper())
    if not connector_class:
        raise ValueError(f"Unsupported service type: {service_type}")
    return connector_class


def get_connector_capabilities(service_type: str) -> dict[str, bool]:
    connector_factory = connector_class(service_type)
    return {
        "supports_databases": bool(getattr(connector_factory, "supports_databases", True)),
        "supports_schemas": bool(getattr(connector_factory, "supports_schemas", True)),
        "supports_tables": bool(getattr(connector_factory, "supports_tables", True)),
        "supports_columns": bool(getattr(connector_factory, "supports_columns", True)),
    }


def get_connector(service_type, username, password, connection_details, database=None, schema=None):
    connector_factory = connector_class(service_type)
    return connector_factory.from_connection(
        username=username,
        password=password,
        connection_details=connection_details or {},
        database=database,
        schema=schema,
    )
