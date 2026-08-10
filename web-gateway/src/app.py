from flask import Flask
from routes.panel import panel_bp
from db import close_pool

def create_app():
    app = Flask(__name__)
    app.register_blueprint(panel_bp)

    @app.teardown_appcontext
    def shutdown(exception=None):
        close_pool()

    return app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)