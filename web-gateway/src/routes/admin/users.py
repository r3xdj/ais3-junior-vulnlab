from flask import Blueprint, jsonify, request

import db
from decorators import require_admin

users_bp = Blueprint('users', __name__, url_prefix='/api/admin')


@users_bp.route('/users', methods=['GET'])
@require_admin
def list_users():
    return jsonify(db.get_all_users())


@users_bp.route('/users/<int:user_id>/role', methods=['POST'])
@require_admin
def update_role(user_id):
    payload = request.get_json(silent=True) or request.form or {}
    role = str(payload.get('role', '')).strip().lower()

    if role not in {'user', 'admin'}:
        return jsonify({"error": "Invalid role"}), 400

    db.update_user_role(user_id, role)
    db.create_activity_log(user_id, f'Role updated to {role}')
    return jsonify({"message": "User role updated"})