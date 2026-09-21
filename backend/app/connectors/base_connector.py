from abc import ABC, abstractmethod


class BaseConnector(ABC):
    """
    Source connector interface used by generic ingestion
    """
    supports_databases = True
    supports_schemas = True
    supports_tables = True
    supports_columns = True

    @classmethod
    def from_connection(cls, username, password, connection_details, database=None, schema=None):
        raise NotImplementedError

    @abstractmethod
    def test_connection(self):
        pass

    @abstractmethod
    def get_databases(self):
        pass

    @abstractmethod
    def get_schemas(self, database=None):
        pass

    @abstractmethod
    def get_tables(self, database=None, schema=None):
        pass

    @abstractmethod
    def get_columns(self, database=None, schema=None, table=None):
        pass
