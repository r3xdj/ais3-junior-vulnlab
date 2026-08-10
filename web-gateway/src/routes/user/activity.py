from flask import Blueprint

activity_bp = Blueprint('activity', __name__, url_prefix='/user')

# TODO: /user/view-activity