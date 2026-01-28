from flask import Blueprint, request, jsonify
from services import settings_manager

settings_bp = Blueprint("settings", __name__)


@settings_bp.route("", methods=["GET"])
def get_settings():
    return jsonify(settings_manager.get_settings())


@settings_bp.route("", methods=["PUT"])
def update_settings():
    data = request.get_json(force=True)
    result = settings_manager.update_settings(data)
    return jsonify(result)
