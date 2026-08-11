import os

from flask import Blueprint, jsonify, request, send_file


material_bp = Blueprint(
    "materials",
    __name__,
    url_prefix="/api/materials",
)


MATERIAL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "assets",
    "materials",
)


@material_bp.get("")
def get_materials():
    return jsonify([
        {
            "name": "Web Security 基礎",
            "file": "web01.pdf",
        }
    ])


@material_bp.post("/read")
def read_material():
    filename = request.form.get("file")

    if not filename:
        return jsonify({
            "error": "missing file"
        }), 400

    path = os.path.join(MATERIAL_DIR, filename)

    if not os.path.isfile(path):
        return jsonify({
            "error": "file not found"
        }), 404

    return send_file(path)
