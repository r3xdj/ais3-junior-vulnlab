from flask import Blueprint, jsonify, request, g
import bcrypt

import db
from decorators import require_login

password_bp = Blueprint('password', __name__, url_prefix='/api/user')


@password_bp.route('/change-password', methods=['POST'])
@require_login
def change_password():
    old_password = request.form.get('old_password', '')
    new_password = request.form.get('new_password', '')

    if not old_password or not new_password:
        return jsonify({"error": "Missing password fields"}), 400

    user = db.get_user_by_id(g.user['sub'])
    if not user or not bcrypt.checkpw(old_password.encode(), user['password_hash'].encode()):
        return jsonify({"error": "Current password is incorrect"}), 401

    hashed_pw = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    db.update_user_password(g.user['sub'], hashed_pw)
    db.create_activity_log(g.user['sub'], 'Changed password')
    return jsonify({"message": "Password updated successfully"})