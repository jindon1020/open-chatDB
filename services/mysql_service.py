from services.connection_manager import manager


def _conn(conn_id: str):
    return manager.get_client(conn_id)


def _ensure_db(conn_id: str, database: str):
    c = _conn(conn_id)
    c.select_db(database)


def list_databases(conn_id: str) -> list[str]:
    c = _conn(conn_id)
    with c.cursor() as cur:
        cur.execute("SHOW DATABASES")
        return [row[next(iter(row))] for row in cur.fetchall()]


def list_tables(conn_id: str, database: str) -> list[str]:
    _ensure_db(conn_id, database)
    c = _conn(conn_id)
    with c.cursor() as cur:
        cur.execute("SHOW TABLES")
        return [row[next(iter(row))] for row in cur.fetchall()]


def get_table_structure(conn_id: str, database: str, table: str) -> list[dict]:
    _ensure_db(conn_id, database)
    c = _conn(conn_id)
    with c.cursor() as cur:
        cur.execute("DESCRIBE `%s`" % table)
        return cur.fetchall()


def get_table_indexes(conn_id: str, database: str, table: str) -> list[dict]:
    _ensure_db(conn_id, database)
    c = _conn(conn_id)
    with c.cursor() as cur:
        cur.execute("SHOW INDEX FROM `%s`" % table)
        return cur.fetchall()


def browse_data(conn_id: str, database: str, table: str,
                page: int = 1, page_size: int = 50) -> dict:
    _ensure_db(conn_id, database)
    c = _conn(conn_id)
    offset = (page - 1) * page_size
    with c.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS cnt FROM `%s`" % table)
        total = cur.fetchone()["cnt"]
        cur.execute("SELECT * FROM `%s` LIMIT %s OFFSET %s" % (table, page_size, offset))
        rows = cur.fetchall()
    return {"rows": rows, "total": total, "page": page, "page_size": page_size}


def execute_query(conn_id: str, sql: str, database: str | None = None) -> dict:
    if database:
        _ensure_db(conn_id, database)
    c = _conn(conn_id)
    with c.cursor() as cur:
        cur.execute(sql)
        if cur.description:
            columns = [d[0] for d in cur.description]
            rows = cur.fetchall()
            return {"columns": columns, "rows": rows, "rowcount": len(rows)}
        else:
            return {"affected_rows": cur.rowcount}


def get_all_schemas(conn_id: str, database: str) -> list[dict]:
    """Return all table schemas for the given database."""
    _ensure_db(conn_id, database)
    c = _conn(conn_id)
    tables_info = []
    with c.cursor() as cur:
        cur.execute("SHOW TABLES")
        table_names = [row[next(iter(row))] for row in cur.fetchall()]
        for tbl in table_names:
            cur.execute("DESCRIBE `%s`" % tbl)
            columns = cur.fetchall()
            tables_info.append({"table": tbl, "columns": columns})
    return tables_info
