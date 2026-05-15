from flask import Flask, redirect, url_for
from flask_socketio import SocketIO

from routes.auth import auth_bp
from routes.workspace import workspace_bp
from routes.channel import channel_bp

socketio = SocketIO()


def create_app():
    app = Flask(__name__)
    app.secret_key = "dev_secret_key"

    app.register_blueprint(auth_bp)
    app.register_blueprint(workspace_bp)
    app.register_blueprint(channel_bp)

    socketio.init_app(app)

    from sockets.channel_socket import register_channel_socket

    register_channel_socket(socketio)

    @app.route("/")
    def home():
        return redirect(url_for("auth.login"))

    return app


app = create_app()


if __name__ == "__main__":
    socketio.run(app, debug=True)
