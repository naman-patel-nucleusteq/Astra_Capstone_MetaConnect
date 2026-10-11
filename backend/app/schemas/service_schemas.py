from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


def reject_numeric_only(value: str | None, field_name: str):
    if value is not None and value.strip() and not any(character.isalpha() for character in value):
        raise ValueError(f"{field_name} must contain at least one letter")
    return value


class ServiceCreate(BaseModel):
    name: str
    description: str | None = None
    service_type: str
    username: str | None = None
    password: str | None = None
    connection_details: dict[str, Any] = Field(default_factory=dict)

    validate_name = field_validator("name")(lambda value: reject_numeric_only(value, "Connection name"))
    validate_description = field_validator("description")(lambda value: reject_numeric_only(value, "Description"))


class ServiceUpdate(BaseModel):
    name: str
    description: str | None = None
    username: str | None = None
    password: str | None = None
    connection_details: dict[str, Any] | None = None

    validate_name = field_validator("name")(lambda value: reject_numeric_only(value, "Connection name"))
    validate_description = field_validator("description")(lambda value: reject_numeric_only(value, "Description"))


class ServiceConnectionTest(BaseModel):
    service_type: str = "SNOWFLAKE"
    username: str | None = None
    password: str | None = None
    connection_details: dict[str, Any] = Field(default_factory=dict)
    account: str | None = None
    warehouse: str | None = None
    role: str | None = None

    @model_validator(mode="before")
    @classmethod
    def include_legacy_snowflake_settings(cls, value):
        if not isinstance(value, dict):
            return value
        if value.get("connection_details") or not any(
            value.get(key) is not None for key in ("account", "warehouse", "role")
        ):
            return value
        return {
            **value,
            "connection_details": {
                key: value[key]
                for key in ("account", "warehouse", "role")
                if value.get(key) is not None
            },
        }


class ConnectorCapabilities(BaseModel):
    supports_databases: bool = True
    supports_schemas: bool = True
    supports_tables: bool = True
    supports_columns: bool = True


class ServiceResponse(BaseModel):
    uuid: UUID
    name: str
    description: str | None = None
    service_type: str
    username: str | None = None
    connection_details: dict[str, Any] | None = None
    airflow_connection_id: str
    created_by: str | None = None
    created_at: datetime
    capabilities: ConnectorCapabilities | None = None

    model_config = {"from_attributes": True}
