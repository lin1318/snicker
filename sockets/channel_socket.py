from flask import session
from flask_socketio import join_room, emit

from db import get_db_connection


def register_channel_socket(socketio):

    @socketio.on("join_channel")
    def join_channel(data):
        cid = data["cid"]

        join_room(f"channel_{cid}")

    @socketio.on("send_message")
    def send_message(data):
        if "user_id" not in session:
            return

        uid = session["user_id"]
        cid = data["cid"]
        content = data["content"]

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO Messages (cid, sender_id, content)
            VALUES (%s, %s, %s)
            RETURNING mid, created_at
            """,
            (cid, uid, content),
        )

        mid, created_at = cur.fetchone()

        cur.execute(
            """
            SELECT username, nickname
            FROM Users
            WHERE uid = %s
            """,
            (uid,),
        )

        username, nickname = cur.fetchone()

        conn.commit()

        cur.close()
        conn.close()

        emit(
            "new_message",
            {
                "mid": mid,
                "content": content,
                "created_at": created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "username": username,
                "nickname": nickname,
            },
            room=f"channel_{cid}",
        )
