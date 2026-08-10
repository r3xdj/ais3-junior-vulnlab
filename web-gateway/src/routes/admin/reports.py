from flask import Blueprint

reports_bp = Blueprint('reports', __name__, url_prefix='/api/admin')

# TODO: /api/admin/fetch-report