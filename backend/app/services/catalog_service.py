from sqlalchemy.orm import Session
from app.database.models import Database, IngestionRun, MetadataColumn, Pipeline, Schema, Service, Table


def tree_node(item, item_type, children=None):
    node = {
        "id": item.uuid if item_type == "connection" else item.id,
        "type": item_type,
        "name": item.name,
        "description": getattr(item, "description", None),
        "tags": getattr(item, "tags", None) or [],
        "created_by": getattr(item, "created_by", None),
        "children": children or [],
    }
    for field in ("data_type", "is_nullable", "ordinal_position", "is_primary_key"):
        if hasattr(item, field):
            node[field] = getattr(item, field)
    return node


def get_overview(db: Session):
    services = db.query(Service).order_by(Service.created_at.desc()).all()
    service_ids = [service.id for service in services]
    databases = db.query(Database).filter(Database.service_id.in_(service_ids)).all() if service_ids else []
    database_ids = [database.id for database in databases]
    schemas = db.query(Schema).filter(Schema.database_id.in_(database_ids)).all() if database_ids else []
    schema_ids = [schema.id for schema in schemas]
    tables = db.query(Table).filter(Table.schema_id.in_(schema_ids)).all() if schema_ids else []
    runs = db.query(IngestionRun).filter(IngestionRun.service_id.in_(service_ids)).order_by(IngestionRun.started_at.desc()).limit(10).all() if service_ids else []
    return {
        "services": len(services),
        "databases": len(databases),
        "schemas": len(schemas),
        "tables": len(tables),
        "runs": [run_payload(run, db) for run in runs],
    }


def run_payload(run: IngestionRun, db: Session):
    service = db.query(Service).filter(Service.id == run.service_id).first()
    pipeline = db.query(Pipeline).filter(Pipeline.id == run.pipeline_id).first() if run.pipeline_id else None
    return {
        "id": run.id,
        "service_uuid": service.uuid if service else None,
        "pipeline_id": str(run.pipeline_id) if run.pipeline_id else None,
        "service_name": service.name if service else "Unknown",
        "name": pipeline.name if pipeline else "Metadata ingestion",
        "dag_id": pipeline.airflow_dag_id if pipeline else None,
        "status": run.status,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "error_message": run.error_message,
        "summary": run.summary,
    }


def get_runs(db: Session):
    runs = db.query(IngestionRun).order_by(IngestionRun.started_at.desc()).all()
    return [run_payload(run, db) for run in runs]


def get_tree(db: Session):
    services = db.query(Service).order_by(Service.name).all()
    databases = db.query(Database).order_by(Database.name).all()
    schemas = db.query(Schema).order_by(Schema.name).all()
    tables = db.query(Table).order_by(Table.name).all()
    columns = db.query(MetadataColumn).order_by(MetadataColumn.ordinal_position).all()

    columns_by_table = {}
    for column in columns:
        columns_by_table.setdefault(column.table_id, []).append(tree_node(column, "column"))

    tables_by_schema = {}
    for table in tables:
        tables_by_schema.setdefault(table.schema_id, []).append(
            tree_node(table, "table", columns_by_table.get(table.id, []))
        )

    schemas_by_database = {}
    for schema in schemas:
        schemas_by_database.setdefault(schema.database_id, []).append(
            tree_node(schema, "schema", tables_by_schema.get(schema.id, []))
        )

    databases_by_service = {}
    for database in databases:
        databases_by_service.setdefault(database.service_id, []).append(
            tree_node(database, "database", schemas_by_database.get(database.id, []))
        )

    services_by_type = {}
    for service in services:
        services_by_type.setdefault(service.service_type.upper(), []).append(
            tree_node(service, "connection", databases_by_service.get(service.id, []))
        )

    roots = []
    for service_type in sorted(services_by_type):
        roots.append({
            "id": f"root-{service_type.lower()}",
            "type": "database_root",
            "name": service_type,
            "description": f"{service_type} data sources",
            "tags": [],
            "created_by": None,
            "children": services_by_type[service_type],
        })

    return {"services": roots}
