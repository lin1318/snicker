from flask import Flask, redirect, url_for
from routes.auth import auth_bp
from routes.workspace import workspace_bp
from routes.channel import channel_bp

app = Flask(__name__)
app.secret_key = "dev_secret_key"

app.register_blueprint(auth_bp)
app.register_blueprint(workspace_bp)

app.register_blueprint(channel_bp)


@app.route("/")
def home():
    return redirect(url_for("auth.login"))


if __name__ == "__main__":
    app.run(debug=True)
