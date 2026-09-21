import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import UUID
from app.connectors.factory import get_connector
from app.core.encryption import decrypt_password
from app.database.database import SessionLocal
from app.database.models import (
    Database,
    IngestionRun,
    MetadataColumn,
    MetadataStaging,
    Pipeline,
    Schema,
    Service,
    Table,
)

log = logging.getLogger(__name__)

ENTITY_DATABASE = "database"
ENTITY_SCHEMA = "schema"
ENTITY_TABLE = "table"
ENTITY_COLUMN = "column"
DEFAULT_SCHEMA_NAME = "default"
MERGE_FIELDS = {
    ENTITY_DATABASE: ["description", "tags"],
    ENTITY_SCHEMA: ["description", "tags"],
    ENTITY_TABLE: ["description", "tags"],
    ENTITY_COLUMN: ["data_type", "is_nullable", "ordinal_position", "is_primary_key", "description", "tags"],
}


@contextmanager
def database_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def now_utc():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def json_safe(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    return value


def source_timestamp(value, fallback):
    if not value:
        return fallback
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)


def as_uuid(value):
    if value is None or isinstance(value, UUID):
        return value
    return UUID(str(value))


def run_context(context):
    ti = context["ti"]
    pipeline_id = ti.xcom_pull(key="pipeline_id", task_ids="load_and_test_connection")
    service_id = ti.xcom_pull(key="service_id", task_ids="load_and_test_connection")
    run_id = ti.xcom_pull(key="ingestion_run_id", task_ids="load_and_test_connection")
    if not pipeline_id or not service_id or not run_id:
        raise ValueError("pipeline_id, service_id, and ingestion_run_id must be present in XCom")
    return as_uuid(pipeline_id), int(service_id), int(run_id)


def get_pipeline(db, pipeline_id):
    pipeline = db.query(Pipeline).filter(Pipeline.id == as_uuid(pipeline_id)).first()
    if not pipeline:
        raise ValueError(f"Pipeline {pipeline_id} not found")
    return pipeline


def get_service(db, service_id):
    service = db.query(Service).filter(Service.id == int(service_id)).first()
    if not service:
        raise ValueError(f"Service with id={service_id} not found")
    return service


def connector_for(service, pipeline):
    if not service.username or not service.encrypted_password:
        raise ValueError("Service must contain a username and encrypted password")
    return get_connector(
        service_type=service.service_type,
        username=service.username,
        password=decrypt_password(service.encrypted_password),
        connection_details=service.connection_details or {},
        database=pipeline.database_name,
        schema=pipeline.schema_name,
    )


def load_pipeline_and_service(pipeline_id):
    with database_session() as db:
        pipeline = get_pipeline(db, pipeline_id)
        service = get_service(db, pipeline.service_id)
        return pipeline, service, connector_for(service, pipeline)


def stage_row(db, run_id, entity_type, status, metadata=None, error_message=None, database_name=None, schema_name=None, table_name=None, column_name=None):
    db.add(
        MetadataStaging(
            ingestion_run_id=run_id,
            entity_type=entity_type,
            database_name=database_name,
            schema_name=schema_name,
            table_name=table_name,
            column_name=column_name,
            metadata_json=json_safe(metadata) if metadata is not None else None,
            status=status,
            error_message=error_message,
        )
    )


def staged_success(db, run_id, entity_type):
    return (
        db.query(MetadataStaging)
        .filter(
            MetadataStaging.ingestion_run_id == run_id,
            MetadataStaging.entity_type == entity_type,
            MetadataStaging.status == "SUCCESS",
        )
        .all()
    )


def object_name(entity_type, item):
    if entity_type == ENTITY_DATABASE:
        return item.get("name")
    if entity_type == ENTITY_SCHEMA:
        return f"{item.get('database_name')}.{item.get('name')}"
    if entity_type == ENTITY_TABLE:
        schema_name = item.get("schema_name") or DEFAULT_SCHEMA_NAME
        return f"{item.get('database_name')}.{schema_name}.{item.get('name')}"
    schema_name = item.get("schema_name") or DEFAULT_SCHEMA_NAME
    return f"{item.get('database_name')}.{schema_name}.{item.get('table_name')}.{item.get('name')}"


def resolve_pipeline_id(context):
    conf = context.get("dag_run").conf if context.get("dag_run") else None
    conf = conf or {}
    if conf.get("pipeline_id"):
        return as_uuid(conf["pipeline_id"])
    dag_id = context["dag"].dag_id
    with database_session() as db:
        pipeline = db.query(Pipeline).filter(Pipeline.airflow_dag_id == dag_id).first()
        if not pipeline:
            raise ValueError(f"Pipeline with airflow_dag_id={dag_id} not found")
        return pipeline.id


def load_and_test_connection(**context):
    pipeline_id = resolve_pipeline_id(context)
    with database_session() as db:
        pipeline = get_pipeline(db, pipeline_id)
        service = get_service(db, pipeline.service_id)
        run = IngestionRun(
            service_id=service.id,
            pipeline_id=pipeline.id,
            status="RUNNING",
            started_at=now_utc(),
            created_by=pipeline.created_by,
        )
        pipeline.status = "RUNNING"
        pipeline.updated_at = now_utc()
        db.add(run)
        db.commit()
        db.refresh(run)
        context["ti"].xcom_push(key="pipeline_id", value=str(pipeline.id))
        context["ti"].xcom_push(key="service_id", value=service.id)
        context["ti"].xcom_push(key="ingestion_run_id", value=run.id)
        connector = connector_for(service, pipeline)

    connector.test_connection()
    log.info("[LOAD_AND_TEST_CONNECTION] Connection tested for pipeline_id=%s service_id=%s", pipeline_id, service.id)


def fetch_databases(**context):
    pipeline_id, service_id, run_id = run_context(context)
    log.info("[FETCH_DATABASES] Starting")
    successful = 0
    failed = 0

    with database_session() as db:
        pipeline = get_pipeline(db, pipeline_id)
        service = get_service(db, service_id)
        connector = connector_for(service, pipeline)

        if not connector.supports_databases:
            log.info("[FETCH_DATABASES] Skipped: connector does not support databases")
            stage_row(
                db,
                run_id,
                ENTITY_DATABASE,
                "SKIPPED",
                error_message="Connector does not support databases",
            )
            db.commit()
            return

        try:
            databases = connector.get_databases()

        except Exception as error:
            failed += 1

            stage_row(
                db,
                run_id,
                ENTITY_DATABASE,
                "FAILED",
                database_name=pipeline.database_name or None,
                error_message=str(error),
            )

            db.commit()

            log.info(
                "[FETCH_DATABASES] %s -> FAILED: %s",
                pipeline.database_name or "*",
                error,
            )
            log.info(
                "[FETCH_DATABASES] Completed: %s successful, %s failed",
                successful,
                failed,
            )

            raise

        # Validate requested database
        requested_database = (pipeline.database_name or "").strip()

        if requested_database:
            matching_databases = [
                item
                for item in databases
                if str(item.get("name", "")).upper()
                == requested_database.upper()
            ]

            if not matching_databases:
                error_message = (
                    f"Database '{requested_database}' does not exist "
                    f"or is not accessible."
                )

                stage_row(
                    db,
                    run_id,
                    ENTITY_DATABASE,
                    "FAILED",
                    database_name=requested_database,
                    error_message=error_message,
                )

                db.commit()

                log.info(
                    "[FETCH_DATABASES] %s -> FAILED: %s",
                    requested_database,
                    error_message,
                )
                log.info(
                    "[FETCH_DATABASES] Completed: %s successful, %s failed",
                    successful,
                    failed + 1,
                )

                raise ValueError(error_message)

            databases = matching_databases

        # Store successful databases
        for item in databases:
            name = item.get("name")

            try:
                stage_row(
                    db,
                    run_id,
                    ENTITY_DATABASE,
                    "SUCCESS",
                    metadata=item,
                    database_name=name,
                )

                successful += 1

                log.info(
                    "[FETCH_DATABASES] %s -> SUCCESS",
                    name,
                )

            except Exception as error:
                failed += 1

                stage_row(
                    db,
                    run_id,
                    ENTITY_DATABASE,
                    "FAILED",
                    database_name=name,
                    error_message=str(error),
                )

                log.info(
                    "[FETCH_DATABASES] %s -> FAILED: %s",
                    name,
                    error,
                )

        db.commit()

    log.info(
        "[FETCH_DATABASES] Completed: %s successful, %s failed",
        successful,
        failed,
    )



def fetch_schemas(**context):
    pipeline_id, service_id, run_id = run_context(context)
    log.info("[FETCH_SCHEMAS] Starting")
    successful = 0
    failed = 0
    skipped = 0

    with database_session() as db:
        pipeline = get_pipeline(db, pipeline_id)
        service = get_service(db, service_id)
        connector = connector_for(service, pipeline)

        if not connector.supports_schemas:
            skipped += 1

            stage_row(
                db,
                run_id,
                ENTITY_SCHEMA,
                "SKIPPED",
                error_message="Connector does not support schemas",
            )

            db.commit()

            log.info(
                "[FETCH_SCHEMAS] Skipped: connector does not support schemas"
            )
            log.info(
                "[FETCH_SCHEMAS] Completed: %s successful, %s failed, %s skipped",
                successful,
                failed,
                skipped,
            )

            return

        # Process each successfully fetched database
        for database in staged_success(
            db,
            run_id,
            ENTITY_DATABASE,
        ):
            database_name = database.database_name

            # Fetch schemas from connector
            try:
                schemas = connector.get_schemas(
                    database=database_name
                )

            except Exception as error:
                failed += 1

                stage_row(
                    db,
                    run_id,
                    ENTITY_SCHEMA,
                    "FAILED",
                    database_name=database_name,
                    error_message=str(error),
                )

                log.info(
                    "[FETCH_SCHEMAS] %s -> FAILED: %s",
                    database_name,
                    error,
                )

 
                continue


            # Validate requested schema
            requested_schema = (pipeline.schema_name or "").strip()

            if requested_schema:
                matching_schemas = [
                    item
                    for item in schemas
                    if str(item.get("name", "")).upper()
                    == requested_schema.upper()
                ]

                if not matching_schemas:
                    error_message = (
                        f"Schema '{requested_schema}' does not exist "
                        f"in database '{database_name}' or is not accessible."
                    )

                    stage_row(
                        db,
                        run_id,
                        ENTITY_SCHEMA,
                        "FAILED",
                        database_name=database_name,
                        schema_name=requested_schema,
                        error_message=error_message,
                    )

                    db.commit()

                    log.info(
                        "[FETCH_SCHEMAS] %s.%s -> FAILED: %s",
                        database_name,
                        requested_schema,
                        error_message,
                    )

                    raise ValueError(error_message)

                # Only ingest the requested schema
                schemas = matching_schemas

  
            # Store successful schemas
            for item in schemas:
                schema_name = item.get("name")

                payload = {
                    **item,
                    "database_name": database_name,
                }

                try:
                    stage_row(
                        db,
                        run_id,
                        ENTITY_SCHEMA,
                        "SUCCESS",
                        metadata=payload,
                        database_name=database_name,
                        schema_name=schema_name,
                    )

                    successful += 1

                    log.info(
                        "[FETCH_SCHEMAS] %s -> SUCCESS",
                        object_name(ENTITY_SCHEMA, payload),
                    )

                except Exception as error:
                    failed += 1

                    stage_row(
                        db,
                        run_id,
                        ENTITY_SCHEMA,
                        "FAILED",
                        database_name=database_name,
                        schema_name=schema_name,
                        error_message=str(error),
                    )

                    log.info(
                        "[FETCH_SCHEMAS] %s.%s -> FAILED: %s",
                        database_name,
                        schema_name,
                        error,
                    )

        db.commit()

    log.info(
        "[FETCH_SCHEMAS] Completed: %s successful, %s failed, %s skipped",
        successful,
        failed,
        skipped,
    )


def fetch_tables(**context):
    pipeline_id, service_id, run_id = run_context(context)
    log.info("[FETCH_TABLES] Starting")
    successful = 0
    failed = 0
    with database_session() as db:
        pipeline = get_pipeline(db, pipeline_id)
        service = get_service(db, service_id)
        connector = connector_for(service, pipeline)
        if not connector.supports_tables:
            log.info("[FETCH_TABLES] Skipped: connector does not support tables")
            stage_row(db, run_id, ENTITY_TABLE, "SKIPPED", error_message="Connector does not support tables")
            db.commit()
            return

        schema_rows = staged_success(db, run_id, ENTITY_SCHEMA)
        if connector.supports_schemas:
            scopes = [
                {"database_name": row.database_name, "schema_name": row.schema_name}
                for row in schema_rows
            ]
        else:
            scopes = [
                {"database_name": row.database_name, "schema_name": None}
                for row in staged_success(db, run_id, ENTITY_DATABASE)
            ]

        for scope in scopes:
            database_name = scope["database_name"]
            schema_name = scope["schema_name"]
            try:
                tables = connector.get_tables(database=database_name, schema=schema_name)
            except Exception as error:
                failed += 1
                stage_row(
                    db,
                    run_id,
                    ENTITY_TABLE,
                    "FAILED",
                    database_name=database_name,
                    schema_name=schema_name,
                    error_message=str(error),
                )
                log.info("[FETCH_TABLES] %s.%s -> FAILED: %s", database_name, schema_name or DEFAULT_SCHEMA_NAME, error)
                continue

            for item in tables:
                table_schema = item.get("schema") if item.get("schema") is not None else schema_name
                payload = {**item, "database_name": database_name, "schema_name": table_schema}
                table_name = item.get("name")
                try:
                    stage_row(
                        db,
                        run_id,
                        ENTITY_TABLE,
                        "SUCCESS",
                        metadata=payload,
                        database_name=database_name,
                        schema_name=table_schema,
                        table_name=table_name,
                    )
                    successful += 1
                    log.info("[FETCH_TABLES] %s -> SUCCESS", table_name)
                except Exception as error:
                    failed += 1
                    stage_row(
                        db,
                        run_id,
                        ENTITY_TABLE,
                        "FAILED",
                        database_name=database_name,
                        schema_name=table_schema,
                        table_name=table_name,
                        error_message=str(error),
                    )
                    log.info("[FETCH_TABLES] %s -> FAILED: %s", table_name, error)

        db.commit()
    log.info("[FETCH_TABLES] Completed: %s successful, %s failed", successful, failed)


def fetch_columns(**context):
    pipeline_id, service_id, run_id = run_context(context)
    log.info("[FETCH_COLUMNS] Starting")
    successful = 0
    failed = 0
    with database_session() as db:
        pipeline = get_pipeline(db, pipeline_id)
        service = get_service(db, service_id)
        connector = connector_for(service, pipeline)
        if not connector.supports_columns:
            log.info("[FETCH_COLUMNS] Skipped: connector does not support columns")
            stage_row(db, run_id, ENTITY_COLUMN, "SKIPPED", error_message="Connector does not support columns")
            db.commit()
            return

        for table in staged_success(db, run_id, ENTITY_TABLE):
            database_name = table.database_name
            schema_name = table.schema_name
            table_name = table.table_name
            try:
                columns = connector.get_columns(
                    database=database_name,
                    schema=schema_name,
                    table=table_name,
                )
            except Exception as error:
                failed += 1
                stage_row(
                    db,
                    run_id,
                    ENTITY_COLUMN,
                    "FAILED",
                    database_name=database_name,
                    schema_name=schema_name,
                    table_name=table_name,
                    error_message=str(error),
                )
                log.info("[FETCH_COLUMNS] %s -> FAILED: %s", table_name, error)
                continue

            for item in columns:
                payload = {
                    **item,
                    "database_name": database_name,
                    "schema_name": schema_name,
                    "table_name": table_name,
                }
                column_name = item.get("name")
                try:
                    stage_row(
                        db,
                        run_id,
                        ENTITY_COLUMN,
                        "SUCCESS",
                        metadata=payload,
                        database_name=database_name,
                        schema_name=schema_name,
                        table_name=table_name,
                        column_name=column_name,
                    )
                    successful += 1
                    log.info("[FETCH_COLUMNS] %s.%s -> SUCCESS", table_name, column_name)
                except Exception as error:
                    failed += 1
                    stage_row(
                        db,
                        run_id,
                        ENTITY_COLUMN,
                        "FAILED",
                        database_name=database_name,
                        schema_name=schema_name,
                        table_name=table_name,
                        column_name=column_name,
                        error_message=str(error),
                    )
                    log.info("[FETCH_COLUMNS] %s.%s -> FAILED: %s", table_name, column_name, error)

        db.commit()
    log.info("[FETCH_COLUMNS] Completed: %s successful, %s failed", successful, failed)


def values_equal(left, right):
    if left is None and right in (None, [], ""):
        return True
    if right is None and left in (None, [], ""):
        return True
    return left == right


def update_record(record, values, fields, timestamp):
    changed = False
    for field in fields:
        value = values.get(field)
        if field == "tags":
            value = value or []
        current = getattr(record, field)
        if field == "tags":
            current = current or []
        if not values_equal(current, value):
            setattr(record, field, value)
            changed = True
    if changed:
        record.updated_at = timestamp
    return changed


def find_record(db, model, filters):
    return db.query(model).filter(*filters).first()


def store_metadata(**context):
    pipeline_id, service_id, run_id = run_context(context)
    timestamp = now_utc()
    counts = {"inserted": 0, "updated": 0, "unchanged": 0}

    with database_session() as db:
        pipeline = get_pipeline(db, pipeline_id)
        created_by = pipeline.created_by
        database_ids = {}
        schema_ids = {}
        table_ids = {}

        for row in staged_success(db, run_id, ENTITY_DATABASE):
            item = row.metadata_json or {}
            name = row.database_name or item.get("name")
            record = find_record(db, Database, [Database.service_id == service_id, Database.name == name])
            if not record:
                record = Database(
                    service_id=service_id,
                    name=name,
                    description=item.get("description"),
                    tags=item.get("tags") or [],
                    created_by=created_by,
                    created_at=source_timestamp(item.get("created_at"), timestamp),
                    updated_at=source_timestamp(item.get("updated_at"), timestamp),
                )
                db.add(record)
                db.flush()
                counts["inserted"] += 1
            elif update_record(record, item, MERGE_FIELDS[ENTITY_DATABASE], timestamp):
                counts["updated"] += 1
            else:
                counts["unchanged"] += 1
            database_ids[name] = record.id

        schema_rows = staged_success(db, run_id, ENTITY_SCHEMA)
        schemas_skipped = (
            db.query(MetadataStaging)
            .filter(
                MetadataStaging.ingestion_run_id == run_id,
                MetadataStaging.entity_type == ENTITY_SCHEMA,
                MetadataStaging.status == "SKIPPED",
            )
            .first()
            is not None
        )
        if schema_rows:
            iterable_schemas = schema_rows
        elif schemas_skipped:
            iterable_schemas = [
                MetadataStaging(
                    database_name=database_name,
                    schema_name=DEFAULT_SCHEMA_NAME,
                    metadata_json={"name": DEFAULT_SCHEMA_NAME, "description": None, "tags": []},
                    status="SUCCESS",
                )
                for database_name in database_ids
            ]
        else:
            iterable_schemas = []

        for row in iterable_schemas:
            item = row.metadata_json or {}
            database_id = database_ids.get(row.database_name)
            if not database_id:
                continue
            schema_name = row.schema_name or item.get("name") or DEFAULT_SCHEMA_NAME
            record = find_record(db, Schema, [Schema.database_id == database_id, Schema.name == schema_name])
            if not record:
                record = Schema(
                    database_id=database_id,
                    name=schema_name,
                    description=item.get("description"),
                    tags=item.get("tags") or [],
                    created_by=created_by,
                    created_at=source_timestamp(item.get("created_at"), timestamp),
                    updated_at=source_timestamp(item.get("updated_at"), timestamp),
                )
                db.add(record)
                db.flush()
                counts["inserted"] += 1
            elif update_record(record, item, MERGE_FIELDS[ENTITY_SCHEMA], timestamp):
                counts["updated"] += 1
            else:
                counts["unchanged"] += 1
            schema_ids[(row.database_name, schema_name)] = record.id

        for row in staged_success(db, run_id, ENTITY_TABLE):
            item = row.metadata_json or {}
            schema_name = row.schema_name or item.get("schema") or DEFAULT_SCHEMA_NAME
            schema_id = schema_ids.get((row.database_name, schema_name))
            if not schema_id:
                continue
            table_name = row.table_name or item.get("name")
            record = find_record(db, Table, [Table.schema_id == schema_id, Table.name == table_name])
            if not record:
                record = Table(
                    schema_id=schema_id,
                    name=table_name,
                    description=item.get("description"),
                    tags=item.get("tags") or [],
                    created_by=created_by,
                    created_at=source_timestamp(item.get("created_at"), timestamp),
                    updated_at=source_timestamp(item.get("updated_at"), timestamp),
                )
                db.add(record)
                db.flush()
                counts["inserted"] += 1
            elif update_record(record, item, MERGE_FIELDS[ENTITY_TABLE], timestamp):
                counts["updated"] += 1
            else:
                counts["unchanged"] += 1
            table_ids[(row.database_name, schema_name, table_name)] = record.id

        for row in staged_success(db, run_id, ENTITY_COLUMN):
            item = row.metadata_json or {}
            schema_name = row.schema_name or DEFAULT_SCHEMA_NAME
            table_id = table_ids.get((row.database_name, schema_name, row.table_name))
            if not table_id:
                continue
            values = {
                "data_type": item.get("data_type"),
                "is_nullable": item.get("is_nullable"),
                "ordinal_position": item.get("ordinal_position"),
                "is_primary_key": item.get("is_primary_key", False),
                "description": item.get("description"),
                "tags": item.get("tags") or [],
            }
            record = find_record(db, MetadataColumn, [MetadataColumn.table_id == table_id, MetadataColumn.name == row.column_name])
            if not record:
                record = MetadataColumn(
                    table_id=table_id,
                    name=row.column_name,
                    created_by=created_by,
                    created_at=timestamp,
                    updated_at=timestamp,
                    **values,
                )
                db.add(record)
                counts["inserted"] += 1
            elif update_record(record, values, MERGE_FIELDS[ENTITY_COLUMN], timestamp):
                counts["updated"] += 1
            else:
                counts["unchanged"] += 1

        run = db.query(IngestionRun).filter(IngestionRun.id == run_id).first()
        if run:
            run.summary = {**(run.summary or {}), "catalog": counts}
        db.commit()

    log.info(
        "[STORE_METADATA] inserted=%s updated=%s unchanged=%s",
        counts["inserted"],
        counts["updated"],
        counts["unchanged"],
    )


def staging_counts(db, run_id):
    rows = db.query(MetadataStaging).filter(MetadataStaging.ingestion_run_id == run_id).all()
    summary = {
        ENTITY_DATABASE: {"successful": 0, "failed": 0, "skipped": 0},
        ENTITY_SCHEMA: {"successful": 0, "failed": 0, "skipped": 0},
        ENTITY_TABLE: {"successful": 0, "failed": 0, "skipped": 0},
        ENTITY_COLUMN: {"successful": 0, "failed": 0, "skipped": 0},
        "failed_objects": [],
    }
    for row in rows:
        bucket = summary.get(row.entity_type)
        if not bucket:
            continue
        if row.status == "SUCCESS":
            bucket["successful"] += 1
        elif row.status == "FAILED":
            bucket["failed"] += 1
            summary["failed_objects"].append({
                "entity_type": row.entity_type,
                "database_name": row.database_name,
                "schema_name": row.schema_name,
                "table_name": row.table_name,
                "column_name": row.column_name,
                "error_message": row.error_message,
            })
        elif row.status == "SKIPPED":
            bucket["skipped"] += 1
    return summary


def final_status(summary):
    failed = sum(summary[entity]["failed"] for entity in (ENTITY_DATABASE, ENTITY_SCHEMA, ENTITY_TABLE, ENTITY_COLUMN))
    successful = sum(summary[entity]["successful"] for entity in (ENTITY_DATABASE, ENTITY_SCHEMA, ENTITY_TABLE, ENTITY_COLUMN))
    if failed and successful:
        return "PARTIAL_SUCCESS"
    if failed and not successful:
        return "FAILED"
    return "SUCCESS"


def update_status(**context):
    pipeline_id, _, run_id = run_context(context)
    with database_session() as db:
        summary = staging_counts(db, run_id)
        run = db.query(IngestionRun).filter(IngestionRun.id == run_id).first()
        if not run:
            raise ValueError(f"IngestionRun {run_id} not found")
        catalog = (run.summary or {}).get("catalog", {"inserted": 0, "updated": 0, "unchanged": 0})
        status = final_status(summary)
        run.status = status
        run.finished_at = now_utc()
        run.summary = {
            "databases": summary[ENTITY_DATABASE],
            "schemas": summary[ENTITY_SCHEMA],
            "tables": summary[ENTITY_TABLE],
            "columns": summary[ENTITY_COLUMN],
            "inserted_metadata_count": catalog.get("inserted", 0),
            "updated_metadata_count": catalog.get("updated", 0),
            "unchanged_metadata_count": catalog.get("unchanged", 0),
            "failed_objects": summary["failed_objects"],
        }
        if status == "FAILED":
            run.error_message = "; ".join(
                item["error_message"] for item in summary["failed_objects"] if item.get("error_message")
            ) or "Metadata ingestion failed"
        pipeline = get_pipeline(db, pipeline_id)
        pipeline.status = "READY"
        pipeline.updated_at = now_utc()
        db.commit()

    log.info("[UPDATE_STATUS] Ingestion summary")
    log.info("[UPDATE_STATUS] databases successful=%s failed=%s skipped=%s", summary[ENTITY_DATABASE]["successful"], summary[ENTITY_DATABASE]["failed"], summary[ENTITY_DATABASE]["skipped"])
    log.info("[UPDATE_STATUS] schemas successful=%s failed=%s skipped=%s", summary[ENTITY_SCHEMA]["successful"], summary[ENTITY_SCHEMA]["failed"], summary[ENTITY_SCHEMA]["skipped"])
    log.info("[UPDATE_STATUS] tables successful=%s failed=%s skipped=%s", summary[ENTITY_TABLE]["successful"], summary[ENTITY_TABLE]["failed"], summary[ENTITY_TABLE]["skipped"])
    log.info("[UPDATE_STATUS] columns successful=%s failed=%s skipped=%s", summary[ENTITY_COLUMN]["successful"], summary[ENTITY_COLUMN]["failed"], summary[ENTITY_COLUMN]["skipped"])
    log.info("[UPDATE_STATUS] inserted=%s updated=%s unchanged=%s", catalog.get("inserted", 0), catalog.get("updated", 0), catalog.get("unchanged", 0))
    for item in summary["failed_objects"]:
        log.info("[UPDATE_STATUS] FAILED %s %s: %s", item["entity_type"], item.get("column_name") or item.get("table_name") or item.get("schema_name") or item.get("database_name"), item.get("error_message"))
    log.info("[UPDATE_STATUS] IngestionRun %s -> %s", run_id, status)


def on_dag_failure(context):
    run_id = None
    try:
        run_id = context["ti"].xcom_pull(key="ingestion_run_id", task_ids="load_and_test_connection")
        pipeline_id = context["ti"].xcom_pull(key="pipeline_id", task_ids="load_and_test_connection")
    except Exception:
        pipeline_id = None
    if not run_id:
        log.warning("No ingestion_run_id found in XCom")
        return
    try:
        with database_session() as db:
            run = db.query(IngestionRun).filter(IngestionRun.id == run_id).first()
            if run:
                run.status = "FAILED"
                run.finished_at = now_utc()
                run.error_message = str(context.get("exception") or "Unknown error")
            if pipeline_id:
                pipeline = db.query(Pipeline).filter(Pipeline.id == as_uuid(pipeline_id)).first()
                if pipeline:
                    pipeline.status = "READY"
                    pipeline.updated_at = now_utc()
            db.commit()
    except Exception:
        log.exception("Failed to update IngestionRun %s as FAILED", run_id)
