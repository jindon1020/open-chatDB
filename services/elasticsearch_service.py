import json
from services.connection_manager import manager


def _client(conn_id: str):
    return manager.get_client(conn_id)


def list_databases(conn_id: str) -> list[str]:
    """ES has no databases; return a single pseudo-database '_all'."""
    return ["_all"]


def list_tables(conn_id: str, database: str = "_all") -> list[str]:
    """List indices as 'tables'."""
    es = _client(conn_id)
    indices = list(es.indices.get(index="*").keys())
    # filter out internal indices
    return [i for i in indices if not i.startswith(".")]


def get_table_structure(conn_id: str, database: str, index: str) -> list[dict]:
    es = _client(conn_id)
    mapping = es.indices.get_mapping(index=index)
    properties = mapping[index]["mappings"].get("properties", {})
    result = []
    for field, info in properties.items():
        result.append({
            "Field": field,
            "Type": info.get("type", "object"),
            "Key": "",
        })
    return result


def browse_data(conn_id: str, database: str, index: str,
                page: int = 1, page_size: int = 50) -> dict:
    es = _client(conn_id)
    from_ = (page - 1) * page_size
    resp = es.search(index=index, body={"query": {"match_all": {}}, "from": from_, "size": page_size})
    hits = resp["hits"]
    rows = []
    for hit in hits["hits"]:
        row = {"_id": hit["_id"], **hit["_source"]}
        rows.append(row)
    total = hits["total"]["value"] if isinstance(hits["total"], dict) else hits["total"]
    return {"rows": rows, "total": total, "page": page, "page_size": page_size}


def execute_query(conn_id: str, query_str: str, database: str | None = None) -> dict:
    """Execute an ES query expressed as JSON.

    Format: {"index": "name", "body": {...ES query body...}}
    """
    try:
        q = json.loads(query_str)
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON: {e}"}

    es = _client(conn_id)
    index = q.get("index", "_all")
    body = q.get("body", {"query": {"match_all": {}}})
    method = q.get("method", "search")

    if method == "search":
        resp = es.search(index=index, body=body)
        rows = [{"_id": h["_id"], **h["_source"]} for h in resp["hits"]["hits"]]
        return {
            "columns": list(rows[0].keys()) if rows else [],
            "rows": rows,
            "rowcount": len(rows),
            "total": resp["hits"]["total"]["value"] if isinstance(resp["hits"]["total"], dict) else resp["hits"]["total"],
        }
    elif method == "index":
        doc = q.get("document", {})
        resp = es.index(index=index, body=doc)
        return {"affected_rows": 1, "result": resp["result"]}
    elif method == "delete":
        doc_id = q.get("id")
        resp = es.delete(index=index, id=doc_id)
        return {"affected_rows": 1, "result": resp["result"]}
    elif method == "update":
        doc_id = q.get("id")
        doc = q.get("document", {})
        resp = es.update(index=index, id=doc_id, body={"doc": doc})
        return {"affected_rows": 1, "result": resp["result"]}
    else:
        return {"error": f"Unsupported method: {method}"}


def get_all_schemas(conn_id: str, database: str = "_all") -> list[dict]:
    indices = list_tables(conn_id, database)
    result = []
    for idx in indices:
        columns = get_table_structure(conn_id, database, idx)
        result.append({"table": idx, "columns": columns})
    return result
