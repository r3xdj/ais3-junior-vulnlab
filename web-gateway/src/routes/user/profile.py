from flask import Blueprint, jsonify, request, g

import db
from decorators import require_login
from certificate_service import regenerate_existing_certificate

profile_bp = Blueprint('profile', __name__, url_prefix='/api/user')


@profile_bp.route('/profile', methods=['GET'])
@require_login
def view_profile():
    profile = db.get_user_profile_by_id(g.user['sub'])
    if not profile:
        return jsonify({"error": "User not found"}), 404
    return jsonify(profile)


@profile_bp.route('/profile', methods=['POST'])
@require_login
def edit_profile():
    payload = request.get_json(silent=True) or request.form or {}
    email = (payload.get('email') or '').strip() or None
    current = db.get_user_by_id(g.user['sub'])
    if not current:
        return jsonify({"error": "User not found"}), 404

    # Display Name 預設為帳號名稱；空白也恢復成 username。
    display_name = (payload.get('display_name') or '').strip() or current['username']
    name_changed = display_name != (current.get('display_name') or current['username'])

    db.update_user_profile(g.user['sub'], email, display_name)
    db.create_activity_log(g.user['sub'], 'Updated profile')

    # 已有證書時，名稱變更會重新排入 PDF 產生佇列。
    if name_changed:
        regenerate_existing_certificate(int(g.user['sub']))

    return jsonify({"message": "Profile updated", "display_name": display_name})