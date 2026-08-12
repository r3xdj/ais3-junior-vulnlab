from .flags import flags_bp
from .users import users_bp
from .webhook import webhook_bp


def register_admin_blueprints(app):
    app.register_blueprint(flags_bp)
    app.register_blueprint(webhook_bp)
    app.register_blueprint(users_bp)
