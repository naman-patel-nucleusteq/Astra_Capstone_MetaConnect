"""Business logic for catalog metadata queries and search."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.database.models import Database, MetadataColumn, Schema, Service, Table
from app.schemas.metadata_schemas import SearchResult


def list_databases(service_uuid: UUID, db: Session):
	service = (
		db.query(Service)
		.filter(Service.uuid == service_uuid)
		.first()
	)

	if service is None:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail=f"Service {service_uuid} not found",
		)

	databases = (
		db.query(Database)
		.filter(Database.service_id == service.id)
		.order_by(Database.name)
		.all()
	)
	return [
		{
			"id": database.id,
			"service_uuid": service.uuid,
			"name": database.name,
			"description": database.description,
			"tags": database.tags,
			"created_by": database.created_by,
			"created_at": database.created_at,
			"updated_at": database.updated_at,
		}
		for database in databases
	]



def list_schemas(db_id: int, db: Session):
	database = (
		db.query(Database)
		.filter(Database.id == db_id)
		.first()
	)

	if database is None:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail=f"Database {db_id} not found",
		)

	return (
		db.query(Schema)
		.filter(Schema.database_id == db_id)
		.order_by(Schema.name)
		.all()
	)



def list_tables(schema_id: int, db: Session):
	schema = (
		db.query(Schema)
		.filter(Schema.id == schema_id)
		.first()
	)

	if schema is None:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail=f"Schema {schema_id} not found",
		)

	return (
		db.query(Table)
		.filter(Table.schema_id == schema_id)
		.order_by(Table.name)
		.all()
	)



def list_columns(table_id: int, db: Session):
	table = (
		db.query(Table)
		.filter(Table.id == table_id)
		.first()
	)

	if table is None:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail=f"Table {table_id} not found",
		)

	return (
		db.query(MetadataColumn)
		.filter(MetadataColumn.table_id == table_id)
		.order_by(MetadataColumn.ordinal_position)
		.all()
	)



def search_catalog(query: str, entity_type: str | None, db: Session):

	results: list[SearchResult] = []
	search_term = f"%{query}%"

	if entity_type in (None, "database"):
		rows = (db.query(Database, Service)
                 .join(Service, Database.service_id == Service.id)
                 .filter(or_(Database.name.ilike(search_term), Database.description.ilike(search_term)))
                 .limit(100)
                 .all())
		results.extend(SearchResult(type="database", id=row.id, name=row.name, description=row.description, tags=row.tags, parent=service.name, path=f"{service.name}.{row.name}", service_name=service.name, created_by=row.created_by, created_at=row.created_at, updated_at=row.updated_at) for row, service in rows)

	if entity_type in (None, "schema"):
		rows = (db.query(Schema, Database, Service)
                 .join(Database, Schema.database_id == Database.id)
				 .join(Service, Database.service_id == Service.id)
                 .filter(or_(Schema.name.ilike(search_term), Schema.description.ilike(search_term)))
                 .limit(100)
                 .all())
		results.extend(SearchResult(type="schema", id=row.id, name=row.name, description=row.description, tags=row.tags, parent=f"{service.name}.{database.name}", path=f"{service.name}.{database.name}.{row.name}", service_name=service.name, created_by=row.created_by, created_at=row.created_at, updated_at=row.updated_at) for row, database, service in rows)

	if entity_type in (None, "table"):
		rows = (db.query(Table, Schema, Database, Service)
                 .join(Schema, Table.schema_id == Schema.id)
                 .join(Database, Schema.database_id == Database.id)
				 .join(Service, Database.service_id == Service.id)
                 .filter(or_(Table.name.ilike(search_term), Table.description.ilike(search_term)))
                 .limit(100)
                 .all())
		results.extend(SearchResult(type="table", id=table.id, name=table.name, description=table.description, tags=table.tags, parent=f"{service.name}.{database.name}.{schema.name}", path=f"{service.name}.{database.name}.{schema.name}.{table.name}", service_name=service.name, created_by=table.created_by, created_at=table.created_at, updated_at=table.updated_at) for table, schema, database, service in rows)

	if entity_type in (None, "column"):
		rows = (db.query(MetadataColumn, Table, Schema, Database, Service)
                 .join(Table, MetadataColumn.table_id == Table.id)
                 .join(Schema, Table.schema_id == Schema.id)
                 .join(Database, Schema.database_id == Database.id)
				 .join(Service, Database.service_id == Service.id)
                 .filter(or_(MetadataColumn.name.ilike(search_term), MetadataColumn.description.ilike(search_term)))
                 .limit(100)
                 .all())
		results.extend(SearchResult(type="column", id=column.id, name=column.name, description=column.description, tags=column.tags, parent=f"{service.name}.{database.name}.{schema.name}.{table.name}", path=f"{service.name}.{database.name}.{schema.name}.{table.name}.{column.name}", service_name=service.name, created_by=column.created_by, created_at=column.created_at, updated_at=column.updated_at, data_type=column.data_type, is_nullable=column.is_nullable, ordinal_position=column.ordinal_position, is_primary_key=column.is_primary_key) for column, table, schema, database, service in rows)

	return results[:100]
