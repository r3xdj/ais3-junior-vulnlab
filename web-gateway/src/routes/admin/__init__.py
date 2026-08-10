from .reports import reports_bp
from .users import users_bp

def register_admin_blueprints(app):
    app.register_blueprint(reports_bp)
    app.register_blueprint(users_bp)