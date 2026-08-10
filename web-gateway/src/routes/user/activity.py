from flask import Blueprint

activity_bp = Blueprint('activity', __name__, url_prefix='/api/user')

# TODO: /api/user/view-activity