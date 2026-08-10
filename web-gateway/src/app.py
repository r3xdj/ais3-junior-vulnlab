import atexit
from flask import Flask
from flask_cors import CORS

from routes.auth import auth_bp
from db import close_pool

def create_app():
    app = Flask(__name__)
    # 開發階段允許 frontend (localhost:3000) 跨域打 API,正式接 Apache 反代後可移除
    CORS(app, supports_credentials=True, origins=["http://localhost:3000"])

    app.register_blueprint(auth_bp)
    return app

app = create_app()
atexit.register(close_pool)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)