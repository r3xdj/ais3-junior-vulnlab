import atexit
from flask import Flask

from routes.auth import auth_bp
from routes.admin import register_admin_blueprints
from routes.user import register_user_blueprints
from db import close_pool
from routes.materials import material_bp

def create_app():
    app = Flask(__name__)
    app.register_blueprint(auth_bp)
    register_admin_blueprints(app)
    register_user_blueprints(app)

    app.register_blueprint(material_bp)
    return app

app = create_app()
atexit.register(close_pool)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
