from flask import Blueprint, render_template, request, redirect, session, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_db_connection

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"]
        username = request.form["username"]
        nickname = request.form["nickname"]
        password = request.form["password"]

        password_hash = generate_password_hash(password)

        conn = get_db_connection()
        cur = conn.cursor()

        try:
            cur.execute(
                """
                INSERT INTO Users (email, username, nickname, password_hash)
                VALUES (%s, %s, %s, %s)
                """,
                (email, username, nickname, password_hash),
            )
            conn.commit()

        except Exception as e:
            conn.rollback()
            return f"Register failed: {e}"

        finally:
            cur.close()
            conn.close()

        return redirect(url_for("auth.login"))

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT uid, email, username, nickname, password_hash
            FROM Users
            WHERE email = %s
            """,
            (email,),
        )

        user = cur.fetchone()

        cur.close()
        conn.close()

        if user and check_password_hash(user[4], password):
            session["user_id"] = user[0]
            session["username"] = user[2]

            return redirect(url_for("workspace.dashboard"))

        flash("Invalid email or password.", "error")
        return redirect(url_for("auth.login"))

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
