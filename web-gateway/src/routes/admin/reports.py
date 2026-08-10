from flask import Blueprint

reports_bp = Blueprint('reports', __name__, url_prefix='/admin')

# TODO: /admin/fetch-report