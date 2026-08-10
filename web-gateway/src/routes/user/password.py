from flask import Blueprint

password_bp = Blueprint('password', __name__, url_prefix='/api/user')

# TODO: /api/user/change-password