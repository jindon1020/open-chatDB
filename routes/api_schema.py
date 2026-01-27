from flask import Blueprint, request, jsonify
from services.schema_indexer import indexer

schema_bp = Blueprint("schema", __name__)


@schema_bp.route("/<conn_id>/<database>/index", methods=["POST"])
def index_schema(conn_id, database):
    try:
        schemas = indexer.index(conn_id, database)
        return jsonify({"tables": len(schemas)})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@schema_bp.route("/<conn_id>/<database>/search", methods=["GET"])
def search_schema(conn_id, database):
    q = request.args.get("q", "")
    kind = request.args.get("kind", "all")
    table = request.args.get("table", None) or None
    results = indexer.search(conn_id, database, q, kind, table=table)
    return jsonify(results)


@schema_bp.route("/<conn_id>/<database>/schemas", methods=["GET"])
def get_schemas(conn_id, database):
    schemas = indexer.get_schemas(conn_id, database)
    return jsonify(schemas)
