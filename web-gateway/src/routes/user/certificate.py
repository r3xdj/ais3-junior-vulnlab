from flask import Blueprint, g, jsonify, send_from_directory
import os

import db
from decorators import require_login

certificate_bp = Blueprint('certificate', __name__, url_prefix='/api/user/certificate')
CERTIFICATE_DIR = os.environ.get('CERTIFICATE_DIR', '/certificates')


def _require_member():
    return g.user.get('role') == 'user'


@certificate_bp.get('')
@require_login
def get_certificate():
    if not _require_member():
        return jsonify({"error": "Forbidden"}), 403

    certificate = db.get_certificate_by_user_id(int(g.user['sub']))
    if not certificate:
        return jsonify({"issued": False, "status": "not_issued"})

    return jsonify({
        "issued": certificate['status'] == 'issued',
        "status": certificate['status'],
        "scores": certificate['scores'],
        "average_score": certificate['average_score'],
        "grade": certificate['grade'],
        "issued_at": certificate['issued_at'],
        "download_url": '/api/user/certificate/download' if certificate['status'] == 'issued' else None,
    })


@certificate_bp.get('/download')
@require_login
def download_certificate():
    if not _require_member():
        return jsonify({"error": "Forbidden"}), 403

    certificate = db.get_certificate_by_user_id(int(g.user['sub']))
    if not certificate or certificate['status'] != 'issued' or not certificate['file_name']:
        return jsonify({"error": "Certificate is not available"}), 404

    file_path = os.path.join(CERTIFICATE_DIR, certificate['file_name'])
    if not os.path.isfile(file_path):
        return jsonify({"error": "Certificate file is not available"}), 404

    return send_from_directory(
        CERTIFICATE_DIR,
        certificate['file_name'],
        as_attachment=True,
        download_name='AIS3-Junior-2026-Certificate.pdf',
    )
