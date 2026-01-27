from flask import Blueprint, request, jsonify
from services.connection_manager import manager
from services import mysql_service, mongo_service, elasticsearch_service

database_bp = Blueprint("database", __name__)

_SERVICE_MAP = {
    "mysql": mysql_service,
    "mongodb": mongo_service,
    "elasticsearch": elasticsearch_service,
}


def _svc(conn_id: str):
    db_type = manager.get_db_type(conn_id)
    svc = _SERVICE_MAP.get(db_type)
    if not svc:
        raise ValueError(f"Unsupported type: {db_type}")
    return svc


@database_bp.route("/<conn_id>/databases", methods=["GET"])
def list_databases(conn_id):
    try:
        dbs = _svc(conn_id).list_databases(conn_id)
        return jsonify(dbs)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@database_bp.route("/<conn_id>/<database>/tables", methods=["GET"])
def list_tables(conn_id, database):
    try:
        tables = _svc(conn_id).list_tables(conn_id, database)
        return jsonify(tables)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@database_bp.route("/<conn_id>/<database>/<table>/structure", methods=["GET"])
def table_structure(conn_id, database, table):
    try:
        structure = _svc(conn_id).get_table_structure(conn_id, database, table)
        return jsonify(structure)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@database_bp.route("/<conn_id>/<database>/<table>/data", methods=["GET"])
def browse_data(conn_id, database, table):
    try:
        page = request.args.get("page", 1, type=int)
        page_size = request.args.get("page_size", 50, type=int)
        result = _svc(conn_id).browse_data(conn_id, database, table,
                                            page=page, page_size=page_size)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@database_bp.route("/<conn_id>/<database>/<table>/indexes", methods=["GET"])
def table_indexes(conn_id, database, table):
    try:
        db_type = manager.get_db_type(conn_id)
        if db_type == "mysql":
            indexes = mysql_service.get_table_indexes(conn_id, database, table)
            return jsonify(indexes)
        return jsonify([])
    except Exception as e:
        return jsonify({"error": str(e)}), 400
