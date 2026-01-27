import json
from bson import ObjectId
from services.connection_manager import manager


class _JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        return super().default(o)


def _serialize(doc):
    """Convert a Mongo document to JSON-safe dict."""
    return json.loads(_JSONEncoder().encode(doc))


def _client(conn_id: str):
    return manager.get_client(conn_id)


def list_databases(conn_id: str) -> list[str]:
    return _client(conn_id).list_database_names()


def list_tables(conn_id: str, database: str) -> list[str]:
    return _client(conn_id)[database].list_collection_names()


def get_table_structure(conn_id: str, database: str, collection: str) -> list[dict]:
    """Sample documents to infer field names and types."""
    coll = _client(conn_id)[database][collection]
    sample = list(coll.find().limit(20))
    field_map: dict[str, set] = {}
    for doc in sample:
        for k, v in doc.items():
            field_map.setdefault(k, set()).add(type(v).__name__)
    return [
        {"Field": k, "Type": "/".join(sorted(v)), "Key": "PRI" if k == "_id" else ""}
        for k, v in field_map.items()
    ]


def browse_data(conn_id: str, database: str, collection: str,
                page: int = 1, page_size: int = 50) -> dict:
    coll = _client(conn_id)[database][collection]
    total = coll.estimated_document_count()
    offset = (page - 1) * page_size
    docs = list(coll.find().skip(offset).limit(page_size))
    rows = [_serialize(d) for d in docs]
    return {"rows": rows, "total": total, "page": page, "page_size": page_size}


def execute_query(conn_id: str, query_str: str, database: str | None = None) -> dict:
    """Execute a MongoDB operation expressed as JSON.

    Expected format:
        {"collection": "name", "method": "find", "filter": {...}, "limit": N}
    Supported methods: find, count, aggregate, insertOne, insertMany,
                       updateOne, updateMany, deleteOne, deleteMany.
    """
    try:
        q = json.loads(query_str)
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON query: {e}"}

    db = _client(conn_id)[database or "test"]
    coll_name = q.get("collection")
    if not coll_name:
        return {"error": "Missing 'collection' in query"}
    coll = db[coll_name]
    method = q.get("method", "find")
    filt = q.get("filter", {})
    limit = q.get("limit", 100)

    if method == "find":
        projection = q.get("projection")
        docs = list(coll.find(filt, projection).limit(limit))
        rows = [_serialize(d) for d in docs]
        return {"columns": list(rows[0].keys()) if rows else [], "rows": rows, "rowcount": len(rows)}
    elif method == "count":
        cnt = coll.count_documents(filt)
        return {"rows": [{"count": cnt}], "columns": ["count"], "rowcount": 1}
    elif method == "aggregate":
        pipeline = q.get("pipeline", [])
        docs = list(coll.aggregate(pipeline))
        rows = [_serialize(d) for d in docs]
        return {"columns": list(rows[0].keys()) if rows else [], "rows": rows, "rowcount": len(rows)}
    elif method == "insertOne":
        result = coll.insert_one(q.get("document", {}))
        return {"affected_rows": 1, "inserted_id": str(result.inserted_id)}
    elif method == "insertMany":
        result = coll.insert_many(q.get("documents", []))
        return {"affected_rows": len(result.inserted_ids)}
    elif method in ("updateOne", "updateMany"):
        update = q.get("update", {})
        fn = coll.update_one if method == "updateOne" else coll.update_many
        result = fn(filt, update)
        return {"affected_rows": result.modified_count}
    elif method in ("deleteOne", "deleteMany"):
        fn = coll.delete_one if method == "deleteOne" else coll.delete_many
        result = fn(filt)
        return {"affected_rows": result.deleted_count}
    else:
        return {"error": f"Unsupported method: {method}"}


def get_all_schemas(conn_id: str, database: str) -> list[dict]:
    collections = list_tables(conn_id, database)
    result = []
    for name in collections:
        columns = get_table_structure(conn_id, database, name)
        result.append({"table": name, "columns": columns})
    return result
