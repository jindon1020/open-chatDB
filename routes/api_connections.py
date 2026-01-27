from flask import Blueprint, request, jsonify
from services.connection_manager import manager

connections_bp = Blueprint("connections", __name__)


@connections_bp.route("", methods=["GET"])
def list_connections():
    configs = manager.list_configs()
    result = []
    for c in configs:
        safe = {k: v for k, v in c.items() if k != "password"}
        safe["connected"] = manager.is_connected(c["id"])
        if "ssh" in c:
            safe["ssh"] = {k: v for k, v in c["ssh"].items() if k != "password"}
        result.append(safe)
    return jsonify(result)


@connections_bp.route("", methods=["POST"])
def create_connection():
    data = request.get_json()
    cfg = manager.save_config(data)
    return jsonify({"id": cfg["id"]}), 201


@connections_bp.route("/<conn_id>", methods=["PUT"])
def update_connection(conn_id):
    data = request.get_json()
    data["id"] = conn_id
    cfg = manager.save_config(data)
    return jsonify({"id": cfg["id"]})


@connections_bp.route("/<conn_id>", methods=["DELETE"])
def delete_connection(conn_id):
    manager.delete_config(conn_id)
    return jsonify({"ok": True})


@connections_bp.route("/<conn_id>/connect", methods=["POST"])
def connect(conn_id):
    try:
        result = manager.connect(conn_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@connections_bp.route("/<conn_id>/disconnect", methods=["POST"])
def disconnect(conn_id):
    manager.disconnect(conn_id)
    return jsonify({"ok": True})


@connections_bp.route("/test", methods=["POST"])
def test_connection():
    data = request.get_json()
    result = manager.test_connection(data)
    status = 200 if result["ok"] else 400
    return jsonify(result), status
