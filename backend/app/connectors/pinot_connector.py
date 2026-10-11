from urllib.parse import quote
from urllib.parse import urlsplit, urlunsplit

import requests

from app.connectors.base_connector import BaseConnector


class PinotConnector(BaseConnector):
    """Discover Pinot tables and their schema fields through the Controller API."""

    supports_databases = True
    supports_schemas = True
    supports_tables = True
    supports_columns = True

    DEFAULT_SCOPE = "default"
    REQUEST_TIMEOUT_SECONDS = 15

    def __init__(
        self,
        username,
        password,
        controller_host,
        controller_port,
        broker_host,
        broker_port,
    ):
        self.username = username
        self.password = password
        self.controller_url = self._build_url(controller_host, controller_port, "Controller")
        self.broker_url = self._build_url(broker_host, broker_port, "Broker")

    @staticmethod
    def _build_url(host, port, label):
        normalized_host = str(host or "").strip().rstrip("/")
        if not normalized_host:
            raise ValueError(f"Pinot {label} host is required")

        try:
            normalized_port = int(port)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Pinot {label} port must be an integer") from exc
        if not 1 <= normalized_port <= 65535:
            raise ValueError(f"Pinot {label} port must be between 1 and 65535")

        if "://" not in normalized_host:
            normalized_host = f"http://{normalized_host}"
        parsed = urlsplit(normalized_host)
        if parsed.port is not None:
            raise ValueError(f"Pinot {label} host must not include a port")
        return urlunsplit((parsed.scheme, f"{parsed.netloc}:{normalized_port}", parsed.path.rstrip("/"), "", ""))

    @classmethod
    def from_connection(cls, username, password, connection_details, database=None, schema=None):
        details = connection_details or {}
        return cls(
            username=username,
            password=password,
            controller_host=details.get("controller_host"),
            controller_port=details.get("controller_port"),
            broker_host=details.get("broker_host"),
            broker_port=details.get("broker_port"),
        )

    def _get(self, base_url, path):
        auth = None
        if self.username or self.password:
            auth = (self.username or "", self.password or "")
        response = requests.get(
            f"{base_url}{path}",
            auth=auth,
            timeout=self.REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response

    def test_connection(self):
        self._get(self.controller_url, "/tables")
        self._get(self.broker_url, "/health")
        return True

    def get_databases(self):
        return [{"name": self.DEFAULT_SCOPE, "description": None, "tags": []}]

    def get_schemas(self, database=None):
        if database and database != self.DEFAULT_SCOPE:
            return []
        return [{"name": self.DEFAULT_SCOPE, "description": None, "tags": []}]

    def get_tables(self, database=None, schema=None):
        if database and database != self.DEFAULT_SCOPE:
            return []
        if schema and schema != self.DEFAULT_SCOPE:
            return []

        payload = self._get(self.controller_url, "/tables").json()
        table_names = payload.get("tables", []) if isinstance(payload, dict) else payload
        tables = []
        seen = set()
        for item in table_names:
            if isinstance(item, dict):
                name = item.get("tableName") or item.get("name")
            else:
                name = item
            if not name or name in seen:
                continue
            seen.add(name)
            tables.append({"name": name, "description": None, "tags": []})
        return tables

    def get_columns(self, database=None, schema=None, table=None):
        if not table:
            raise ValueError("table is required to fetch Pinot columns")

        schema_name = self._schema_name_for_table(table)
        payload = self._get(
            self.controller_url,
            f"/schemas/{quote(schema_name, safe='')}",
        ).json()

        fields = []
        for key in ("dimensionFieldSpecs", "metricFieldSpecs", "dateTimeFieldSpecs"):
            fields.extend(payload.get(key, []) or [])

        columns = []
        seen = set()
        for field in fields:
            name = field.get("name")
            if not name or name in seen:
                continue
            seen.add(name)
            columns.append(
                {
                    "name": name,
                    "data_type": field.get("dataType") or field.get("data_type") or "UNKNOWN",
                    "is_nullable": bool(field.get("isNullable", True)),
                    "ordinal_position": len(columns) + 1,
                    "is_primary_key": bool(field.get("isPrimaryKey", False)),
                    "description": field.get("description"),
                    "tags": [],
                }
            )
        return columns

    @staticmethod
    def _schema_name_for_table(table):
        for suffix in ("_OFFLINE", "_REALTIME"):
            if table.upper().endswith(suffix):
                return table[: -len(suffix)]
        return table
