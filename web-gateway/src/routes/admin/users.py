import logging
import os

from flask import Blueprint, jsonify, request

import db
from decorators import require_admin
from certificate_service import queue_certificate_generation

users_bp = Blueprint('users', __name__, url_prefix='/api/admin')
logger = logging.getLogger(__name__)


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

@users_bp.route('/users/<int:user_id>/certificate', methods=['POST'])
@require_admin
def issue_certificate(user_id):
    payload = request.get_json(silent=True) or request.form or {}
    user = db.get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    if user['role'] != 'user':
        return jsonify({"error": "Certificates can only be issued to members"}), 400

    raw_scores = payload.get('scores', payload)
    if not isinstance(raw_scores, dict):
        return jsonify({"error": "scores must be an object"}), 400

    scores = {}
    for field in db.CERTIFICATE_SCORE_FIELDS:
        value = raw_scores.get(field)
        try:
            score = float(value)
        except (TypeError, ValueError):
            return jsonify({"error": f"Missing or invalid score: {field}"}), 400
        if not 0 <= score <= 100:
            return jsonify({"error": f"Score must be between 0 and 100: {field}"}), 400
        scores[field] = int(score) if score.is_integer() else score

    certificate = db.create_or_update_certificate(user_id, scores)
    db.create_activity_log(user_id, f"Certificate scores recorded; issuance queued (grade {certificate['grade']})")

    try:
        queue_certificate_generation(certificate, user)
    except Exception:
        logger.exception('Failed to queue certificate generation for certificate_id=%s', certificate['id'])
        db.update_certificate_status(certificate['id'], 'failed')
        return jsonify({"error": "Certificate generation could not be queued"}), 503

    return jsonify({
        "message": "Certificate issuance queued",
        "certificate": certificate,
    }), 202
