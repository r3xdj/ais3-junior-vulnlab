from flask import Blueprint

profile_bp = Blueprint('profile', __name__, url_prefix='/user')

# TODO: /user/view-profile