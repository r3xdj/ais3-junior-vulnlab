from flask import Blueprint, jsonify, g

import db
from decorators import require_login

activity_bp = Blueprint('activity', __name__, url_prefix='/api/user')


@activity_bp.route('/activity', methods=['GET'])
@require_login
def view_activity():
    logs = db.get_user_activity_logs(g.user['sub'])
    return jsonify(logs)