from .profile import profile_bp
from .activity import activity_bp
from .password import password_bp
from .certificate import certificate_bp

def register_user_blueprints(app):
    app.register_blueprint(profile_bp)
    app.register_blueprint(activity_bp)
    app.register_blueprint(password_bp)
    app.register_blueprint(certificate_bp)
