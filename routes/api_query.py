from flask import Blueprint, request, jsonify
from services.connection_manager import manager
from services import mysql_service, mongo_service, elasticsearch_service
from services.llm_service import is_write_operation
import json
import datetime

query_bp = Blueprint("query", __name__)

_SERVICE_MAP = {
    "mysql": mysql_service,
    "mongodb": mongo_service,
    "elasticsearch": elasticsearch_service,
}


class _Encoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, (datetime.date, datetime.datetime)):
            return o.isoformat()
        if isinstance(o, datetime.timedelta):
            return str(o)
        if isinstance(o, bytes):
            return o.decode("utf-8", errors="replace")
        if isinstance(o, set):
            return list(o)
        return super().default(o)


@query_bp.route("/execute", methods=["POST"])
def execute():
    data = request.get_json()
    conn_id = data.get("conn_id")
    database = data.get("database")
    query_text = data.get("query", "").strip()
    confirmed = data.get("confirmed", False)

    if not conn_id or not query_text:
        return jsonify({"error": "conn_id and query are required"}), 400

    db_type = manager.get_db_type(conn_id)

    # Safety: check for write operations
    if is_write_operation(query_text, db_type) and not confirmed:
        return jsonify({
            "needs_confirmation": True,
            "message": "This is a write operation. Please confirm execution.",
            "query": query_text,
        }), 200

    svc = _SERVICE_MAP.get(db_type)
    if not svc:
        return jsonify({"error": f"Unsupported type: {db_type}"}), 400

    try:
        result = svc.execute_query(conn_id, query_text, database)
        # Serialize with custom encoder for dates/bytes
        return _Encoder().encode(result), 200, {"Content-Type": "application/json"}
    except Exception as e:
        return jsonify({"error": str(e)}), 400
