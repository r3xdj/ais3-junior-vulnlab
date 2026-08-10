from .profile import profile_bp
from .activity import activity_bp

def register_user_blueprints(app):
    app.register_blueprint(profile_bp)
    app.register_blueprint(activity_bp)