import threading
from services.connection_manager import manager
from services import mysql_service, mongo_service, elasticsearch_service

_SERVICE_MAP = {
    "mysql": mysql_service,
    "mongodb": mongo_service,
    "elasticsearch": elasticsearch_service,
}


class SchemaIndexer:
    """In-memory cache of database schemas for autocomplete."""

    def __init__(self):
        self._lock = threading.Lock()
        # key = (conn_id, database), value = list[{table, columns}]
        self._cache: dict[tuple[str, str], list[dict]] = {}

    def index(self, conn_id: str, database: str) -> list[dict]:
        db_type = manager.get_db_type(conn_id)
        svc = _SERVICE_MAP.get(db_type)
        if not svc:
            raise ValueError(f"Unsupported db type: {db_type}")
        schemas = svc.get_all_schemas(conn_id, database)
        with self._lock:
            self._cache[(conn_id, database)] = schemas
        return schemas

    def get_schemas(self, conn_id: str, database: str) -> list[dict]:
        with self._lock:
            return self._cache.get((conn_id, database), [])

    def search(self, conn_id: str, database: str, query: str, kind: str = "all", table: str = None) -> list[dict]:
        """Fuzzy search tables and fields.

        kind: "table", "field", or "all"
        table: if specified, only return fields from this table
        Returns list of {"type": "table"|"field", "table": ..., "field": ..., "display": ...}
        """
        schemas = self.get_schemas(conn_id, database)
        q = query.lower()
        results = []
        for tbl in schemas:
            tbl_name = tbl["table"]
            if kind in ("table", "all") and q in tbl_name.lower():
                results.append({
                    "type": "table",
                    "table": tbl_name,
                    "field": None,
                    "display": tbl_name,
                })
            if kind in ("field", "all"):
                if table and tbl_name.lower() != table.lower():
                    continue
                for col in tbl.get("columns", []):
                    field_name = col.get("Field", "")
                    if q in field_name.lower():
                        results.append({
                            "type": "field",
                            "table": tbl_name,
                            "field": field_name,
                            "display": field_name if table else f"{tbl_name}.{field_name}",
                        })
        return results

    def build_schema_text(self, conn_id: str, database: str) -> str:
        """Build a compact text representation of all schemas for LLM prompts."""
        schemas = self.get_schemas(conn_id, database)
        if not schemas:
            schemas = self.index(conn_id, database)
        lines = [f"Database: {database}", ""]
        for tbl in schemas:
            cols = ", ".join(
                f"{c.get('Field', '?')} {c.get('Type', '')}" for c in tbl.get("columns", [])
            )
            lines.append(f"  {tbl['table']}({cols})")
        return "\n".join(lines)


indexer = SchemaIndexer()
