from flask import Blueprint

profile_bp = Blueprint('profile', __name__, url_prefix='/api/user')

# TODO: /api/user/view-profile