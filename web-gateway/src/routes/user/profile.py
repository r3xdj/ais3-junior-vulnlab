from flask import Blueprint, jsonify, request, g

import db
from decorators import require_login

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
    display_name = (payload.get('display_name') or '').strip() or None

    db.update_user_profile(g.user['sub'], email, display_name)
    db.create_activity_log(g.user['sub'], 'Updated profile')
    return jsonify({"message": "Profile updated"})