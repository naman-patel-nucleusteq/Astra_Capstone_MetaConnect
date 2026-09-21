import uuid as uuid_lib
from sqlalchemy import Column as SQLColumn, BigInteger, Integer, String, Boolean, TIMESTAMP, ForeignKey, Text, text
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import JSONB, UUID

Base = declarative_base()


# Service
class Service(Base):
    __tablename__ = "services"

    id = SQLColumn(BigInteger, primary_key=True)
    uuid = SQLColumn(UUID(as_uuid=True), nullable=False, unique=True, default=uuid_lib.uuid4)
    name = SQLColumn(String(100), nullable=False, unique=True)
    description = SQLColumn(Text)
    tags = SQLColumn(JSONB)
    service_type = SQLColumn(String(50), nullable=False)
    username = SQLColumn(String(100))
    encrypted_password = SQLColumn(Text)
    connection_details = SQLColumn(JSONB)
    airflow_connection_id = SQLColumn(String(100), nullable=False)
    created_by = SQLColumn(String(100))
    created_at = SQLColumn(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    databases = relationship("Database", back_populates="service")
    ingestion_runs = relationship("IngestionRun", back_populates="service")
    pipelines = relationship("Pipeline", back_populates="service")


# Pipeline
class Pipeline(Base):
    __tablename__ = "pipelines"

    id = SQLColumn(UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4)
    service_id = SQLColumn(BigInteger, ForeignKey("services.id"), nullable=False)
    name = SQLColumn(String(250), nullable=False)
    airflow_dag_id = SQLColumn(String(250), nullable=False, unique=True)
    database_name = SQLColumn(String(200))
    schema_name = SQLColumn(String(200))
    schedule_type = SQLColumn(String(20), nullable=False, default="MANUAL")
    schedule = SQLColumn(String(120))
    status = SQLColumn(String(30), nullable=False, default="CREATED")
    created_by = SQLColumn(String(100))
    created_at = SQLColumn(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = SQLColumn(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    service = relationship("Service", back_populates="pipelines")
    ingestion_runs = relationship("IngestionRun", back_populates="pipeline")


# Database
class Database(Base):
    __tablename__ = "databases"

    id = SQLColumn(BigInteger, primary_key=True)
    service_id = SQLColumn(BigInteger, ForeignKey("services.id"), nullable=False)
    name = SQLColumn(String(100), nullable=False)
    description = SQLColumn(Text)
    tags = SQLColumn(JSONB)
    created_by = SQLColumn(String(100))
    created_at = SQLColumn(TIMESTAMP, nullable=False)
    updated_at = SQLColumn(TIMESTAMP, nullable=False)

    service = relationship("Service", back_populates="databases")
    schemas = relationship("Schema", back_populates="database")


# Schema
class Schema(Base):
    __tablename__ = "schemas"

    id = SQLColumn(BigInteger, primary_key=True)
    database_id = SQLColumn(BigInteger, ForeignKey("databases.id"), nullable=False)
    name = SQLColumn(String(100), nullable=False)
    description = SQLColumn(Text)
    tags = SQLColumn(JSONB)
    created_by = SQLColumn(String(100))
    created_at = SQLColumn(TIMESTAMP, nullable=False)
    updated_at = SQLColumn(TIMESTAMP, nullable=False)

    database = relationship("Database", back_populates="schemas")
    tables = relationship("Table", back_populates="schema")


# Table
class Table(Base):
    __tablename__ = "tables"

    id = SQLColumn(BigInteger, primary_key=True)
    schema_id = SQLColumn(BigInteger, ForeignKey("schemas.id"), nullable=False)
    name = SQLColumn(String(200), nullable=False)
    description = SQLColumn(Text)
    tags = SQLColumn(JSONB)
    created_by = SQLColumn(String(100))
    created_at = SQLColumn(TIMESTAMP, nullable=False)
    updated_at = SQLColumn(TIMESTAMP, nullable=False)

    schema = relationship("Schema", back_populates="tables")
    columns = relationship("MetadataColumn", back_populates="table")


# Column
class MetadataColumn(Base):
    __tablename__ = "columns"

    id = SQLColumn(BigInteger, primary_key=True)
    table_id = SQLColumn(BigInteger, ForeignKey("tables.id"), nullable=False)
    name = SQLColumn(String(200), nullable=False)
    data_type = SQLColumn(String(100), nullable=False)
    is_nullable = SQLColumn(Boolean, nullable=False)
    ordinal_position = SQLColumn(Integer, nullable=False)
    is_primary_key = SQLColumn(Boolean, nullable=False, default=False)
    description = SQLColumn(Text)
    tags = SQLColumn(JSONB)
    created_by = SQLColumn(String(100))
    created_at = SQLColumn(TIMESTAMP, nullable=False)
    updated_at = SQLColumn(TIMESTAMP, nullable=False)

    table = relationship("Table", back_populates="columns")


# Ingestion Run
class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id = SQLColumn(BigInteger, primary_key=True)
    service_id = SQLColumn(BigInteger, ForeignKey("services.id"), nullable=False)
    pipeline_id = SQLColumn(UUID(as_uuid=True), ForeignKey("pipelines.id"))
    status = SQLColumn(String(20), nullable=False)
    started_at = SQLColumn(TIMESTAMP, nullable=False)
    finished_at = SQLColumn(TIMESTAMP)
    error_message = SQLColumn(Text)
    summary = SQLColumn(JSONB)
    created_by = SQLColumn(String(100))

    service = relationship("Service", back_populates="ingestion_runs")
    pipeline = relationship("Pipeline", back_populates="ingestion_runs")
    staging_rows = relationship("MetadataStaging", back_populates="ingestion_run")


# Metadata Staging
class MetadataStaging(Base):
    __tablename__ = "metadata_staging"

    id = SQLColumn(BigInteger, primary_key=True)
    ingestion_run_id = SQLColumn(BigInteger, ForeignKey("ingestion_runs.id"), nullable=False)
    entity_type = SQLColumn(String(20), nullable=False)
    database_name = SQLColumn(String(200))
    schema_name = SQLColumn(String(200))
    table_name = SQLColumn(String(200))
    column_name = SQLColumn(String(200))
    metadata_json = SQLColumn(JSONB)
    status = SQLColumn(String(20), nullable=False)
    error_message = SQLColumn(Text)
    created_at = SQLColumn(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    ingestion_run = relationship("IngestionRun", back_populates="staging_rows")
