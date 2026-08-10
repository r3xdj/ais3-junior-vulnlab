import atexit
from flask import Flask
from flask_cors import CORS

from routes.auth import auth_bp
from db import close_pool

def create_app():
    app = Flask(__name__)
    app.register_blueprint(auth_bp)
    return app

app = create_app()
atexit.register(close_pool)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)