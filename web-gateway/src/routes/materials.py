import os

from flask import Blueprint, jsonify, request, send_file
from decorators import require_login


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
@require_login
def get_materials():
    return jsonify([
        {
            "name": "Web Security 基礎",
            "file": "web_security.pdf",
        },
        {
            "name": "傑鋒的男友教戰手冊：資安長不告訴你的祕密",
            "file": "boyfriend_manual.pdf",
        },
        {
            "name": "Pwn 入門",
            "file": "pwn01.pdf",
        },
        {
            "name": "我好電：紅隊演練實習生經驗分享",
            "file": "red_team_intern.pdf",
        }
    ])


@material_bp.post("/read")
@require_login
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
