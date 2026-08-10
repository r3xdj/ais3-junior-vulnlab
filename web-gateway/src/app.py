from flask import Flask
from routes.auth import auth_bp
from routes.panel import panel_bp
from routes.admin import register_admin_blueprints
from routes.user import register_user_blueprints

def create_app():
    app = Flask(__name__)
    app.register_blueprint(auth_bp)
    app.register_blueprint(panel_bp)
    register_admin_blueprints(app)
    register_user_blueprints(app)
    return app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)