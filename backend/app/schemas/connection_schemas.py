from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any


# Snowflake connection schemas

class SnowflakeConnection(BaseModel):
    username: str
    password: str
    account: str
    warehouse: str
    database: str | None = None
    schema_name: str | None = Field(default=None, alias="schema")
    role: str | None = None


class SnowflakeDatabaseRequest(BaseModel):
    username: str
    password: str
    account: str
    warehouse: str
    database: str | None = None
    role: str | None = None


class SnowflakeSchemaRequest(BaseModel):
    username: str
    password: str
    account: str
    warehouse: str
    database: str
    schema_name: str | None = Field(default=None, alias="schema")
    role: str | None = None


class SnowflakeTableRequest(BaseModel):
    username: str
    password: str
    account: str
    warehouse: str
    database: str
    schema_name: str | None = Field(alias="schema")
    role: str | None = None


class SnowflakeColumnRequest(BaseModel):
    username: str
    password: str
    account: str
    warehouse: str
    database: str
    schema_name: str | None = Field(alias="schema")
    table: str
    role: str | None = None

