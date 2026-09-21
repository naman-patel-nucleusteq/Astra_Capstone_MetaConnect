import snowflake.connector
from app.connectors.base_connector import BaseConnector


class SnowflakeConnector(BaseConnector):
    supports_databases = True
    supports_schemas = True
    supports_tables = True
    supports_columns = True

    def __init__(self, username, password, account, warehouse, database=None, schema=None, role=None):
        self.username = username
        self.password = password
        self.account = account
        self.warehouse = warehouse
        self.database = database
        self.schema = schema
        self.role = role

    @classmethod
    def from_connection(cls, username, password, connection_details, database=None, schema=None):
        details = connection_details or {}
        return cls(
            username=username,
            password=password,
            account=details.get("account"),
            warehouse=details.get("warehouse"),
            database=database,
            schema=schema,
            role=details.get("role"),
        )

    def connect(self, database=None, schema=None):
        return snowflake.connector.connect(
            user=self.username,
            password=self.password,
            account=self.account,
            warehouse=self.warehouse,
            database=database,
            schema=schema,
            role=self.role,
        )

    def format_tag(self, tag_row):
        tag_name, tag_value = tag_row[0], tag_row[1]
        return f"{tag_name}:{tag_value}" if tag_value is not None else tag_name

    @staticmethod
    def quote_identifier(identifier):
        value = str(identifier or "")
        if not value:
            raise ValueError("Snowflake identifier cannot be empty")
        return '"' + value.replace('"', '""') + '"'

    def direct_tags(self, cursor, object_name, object_type, catalog=None):
        """
        Return tags assigned directly to the object, excluding inherited tags
        """
        tag_catalog = catalog or self.database
        if not tag_catalog:
            return []
        try:
            cursor.execute(
                f"""
                SELECT TAG_NAME, TAG_VALUE
                FROM TABLE({self.quote_identifier(tag_catalog)}.INFORMATION_SCHEMA.TAG_REFERENCES(%s, %s))
                WHERE LEVEL = %s AND APPLY_METHOD = 'MANUAL'
                """,
                (object_name, object_type, object_type),
            )
            return [self.format_tag(row) for row in cursor.fetchall()]
        except Exception:
            return []


    def test_connection(self):
        connection = self.connect(database=self.database, schema=self.schema)
        connection.close()
        return True


    def get_databases(self):
        connection = self.connect()
        cursor = connection.cursor()

        if self.database:
            cursor.execute(
                """
                SELECT DATABASE_NAME, COMMENT, CREATED, LAST_ALTERED
                FROM SNOWFLAKE.INFORMATION_SCHEMA.DATABASES
                WHERE DATABASE_NAME = %s
                ORDER BY DATABASE_NAME
                """,
                (self.database,),
            )
        else:
            cursor.execute(
                """
                SELECT DATABASE_NAME, COMMENT, CREATED, LAST_ALTERED
                FROM SNOWFLAKE.INFORMATION_SCHEMA.DATABASES
                ORDER BY DATABASE_NAME
                """
            )

        database_rows = cursor.fetchall()
        databases = []

        for row in database_rows:
            database_name = row[0]
            tags = self.direct_tags(cursor, database_name, "DATABASE", catalog=database_name)
            databases.append({
                "name": database_name,
                "description": row[1],
                "tags": tags,
                "created_by": None,
                "created_at": row[2],
                "updated_at": row[3],
            })

        cursor.close()
        connection.close()
        return databases


    def get_schemas(self, database=None):
        database_name = database or self.database
        if not database_name:
            raise ValueError("database is required to fetch Snowflake schemas")

        connection = self.connect()
        cursor = connection.cursor()
        quoted_database = self.quote_identifier(database_name)
        schema_filter = self.schema

        if schema_filter:
            cursor.execute(
                f"""
                SELECT SCHEMA_NAME, COMMENT, CREATED, LAST_ALTERED
                FROM {quoted_database}.INFORMATION_SCHEMA.SCHEMATA
                WHERE SCHEMA_NAME = %s
                ORDER BY SCHEMA_NAME
                """,
                (schema_filter,),
            )
        else:
            cursor.execute(
                f"""
                SELECT SCHEMA_NAME, COMMENT, CREATED, LAST_ALTERED
                FROM {quoted_database}.INFORMATION_SCHEMA.SCHEMATA
                ORDER BY SCHEMA_NAME
                """
            )

        schema_rows = cursor.fetchall()
        schemas = []

        for row in schema_rows:
            schema_name = row[0]
            tags = self.direct_tags(
                cursor,
                f"{database_name}.{schema_name}",
                "SCHEMA",
                catalog=database_name,
            )
            schemas.append({
                "name": schema_name,
                "description": row[1],
                "tags": tags,
                "created_by": None,
                "created_at": row[2],
                "updated_at": row[3],
            })

        cursor.close()
        connection.close()
        return schemas


    def get_tables(self, database=None, schema=None):
        database_name = database or self.database
        schema_name = schema if schema is not None else self.schema
        if not database_name:
            raise ValueError("database is required to fetch Snowflake tables")

        connection = self.connect(database=database_name)
        cursor = connection.cursor()
        quoted_database = self.quote_identifier(database_name)

        if schema_name:
            cursor.execute(
                f"""
                SELECT TABLE_SCHEMA, TABLE_NAME, COMMENT, CREATED, LAST_ALTERED
                FROM {quoted_database}.INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = %s
                ORDER BY TABLE_SCHEMA, TABLE_NAME
                """,
                (schema_name,),
            )
        else:
            cursor.execute(
                f"""
                SELECT TABLE_SCHEMA, TABLE_NAME, COMMENT, CREATED, LAST_ALTERED
                FROM {quoted_database}.INFORMATION_SCHEMA.TABLES
                ORDER BY TABLE_SCHEMA, TABLE_NAME
                """
            )

        table_rows = cursor.fetchall()
        tables = []

        for row in table_rows:
            table_schema = row[0]
            table_name = row[1]
            tags = self.direct_tags(
                cursor,
                f"{database_name}.{table_schema}.{table_name}",
                "TABLE",
                catalog=database_name,
            )
            tables.append({
                "schema": table_schema,
                "name": table_name,
                "description": row[2],
                "tags": tags,
                "created_by": None,
                "created_at": row[3],
                "updated_at": row[4],
            })

        cursor.close()
        connection.close()
        return tables


    def get_columns(self, database=None, schema=None, table=None):
        if not table:
            raise ValueError("table is required to fetch Snowflake columns")

        table_parts = str(table).split(".")
        table_name = table_parts[-1]
        table_database = table_parts[-3] if len(table_parts) >= 3 else (database or self.database)
        table_schema = table_parts[-2] if len(table_parts) >= 2 else (schema or self.schema)
        if not table_database or not table_schema:
            raise ValueError("database and schema are required to fetch Snowflake columns")

        object_table = ".".join((table_database, table_schema, table_name))
        qualified_table = ".".join(
            self.quote_identifier(part)
            for part in (table_database, table_schema, table_name)
        )
        connection = self.connect(database=table_database, schema=table_schema)
        cursor = connection.cursor()
        cursor.execute(f"DESCRIBE TABLE {qualified_table}")
        column_rows = cursor.fetchall()

        column_tags = {}
        try:
            cursor.execute(
                f"""
                SELECT TAG_NAME, TAG_VALUE, COLUMN_NAME, LEVEL, APPLY_METHOD
                FROM TABLE({self.quote_identifier(table_database)}.INFORMATION_SCHEMA.TAG_REFERENCES_ALL_COLUMNS(%s, 'TABLE'))
                """,
                (object_table,),
            )
            for row in cursor.fetchall():
                if str(row[3] or "").upper() != "COLUMN" or str(row[4] or "").upper() != "MANUAL":
                    continue
                tag_name = row[0]
                tag_value = row[1]
                column_name = row[2]
                tag = f"{tag_name}:{tag_value}" if tag_value is not None else tag_name
                column_tags.setdefault(column_name.upper(), []).append(tag)
        except Exception:
            column_tags = {}

        columns = []
        for row in column_rows:
            column_name = row[0]
            columns.append({
                "name": column_name,
                "data_type": row[1],
                "is_nullable": row[3] == "Y",
                "ordinal_position": len(columns) + 1,
                "is_primary_key": row[5] == "Y",
                "description": row[9],
                "tags": column_tags.get(column_name.upper(), []),
                "created_by": None,
            })

        cursor.close()
        connection.close()
        return columns
