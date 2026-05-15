from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from db import get_db_connection

channel_bp = Blueprint("channel", __name__)


@channel_bp.route("/channels/create/<int:wid>", methods=["POST"])
def create_channel(wid):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    uid = session["user_id"]

    cname = request.form["cname"]
    ctype = request.form["ctype"]

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT 1
            FROM WorkspaceMembership
            WHERE wid = %s AND uid = %s
            """,
            (wid, uid),
        )

        member = cur.fetchone()

        if not member:
            flash("You are not a member of this workspace.", "error")
            return redirect(url_for("workspace.workspace_detail", wid=wid))

        cur.execute(
            """
            INSERT INTO Channels (wid, cname, ctype, creator_id)
            VALUES (%s, %s, %s, %s)
            RETURNING cid
            """,
            (wid, cname, ctype, uid),
        )

        cid = cur.fetchone()[0]

        cur.execute(
            """
            INSERT INTO ChannelMembers (cid, uid)
            VALUES (%s, %s)
            """,
            (cid, uid),
        )

        conn.commit()

        flash("Channel created successfully.", "success")

    except Exception as e:
        conn.rollback()

        flash(f"Create channel failed: {e}", "error")

    finally:
        cur.close()
        conn.close()

    return redirect(url_for("workspace.workspace_detail", wid=wid))


@channel_bp.route("/channels/<int:cid>")
def channel_detail(cid):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    uid = session["user_id"]

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT c.cid, c.cname, c.ctype, c.wid
        FROM Channels c
        JOIN WorkspaceMembership wm
            ON c.wid = wm.wid
           AND wm.uid = %s
        WHERE c.cid = %s
        """,
        (uid, cid),
    )
    channel = cur.fetchone()

    if not channel:
        cur.close()
        conn.close()

        flash("Channel not found or you do not have access.", "error")
        return redirect(url_for("workspace.dashboard"))

    cid, cname, ctype, wid = channel

    if ctype == "public":
        cur.execute(
            """
            INSERT INTO ChannelMembers (cid, uid)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
            """,
            (cid, uid),
        )
        conn.commit()

    else:
        cur.execute(
            """
            SELECT 1
            FROM ChannelMembers
            WHERE cid = %s AND uid = %s
            """,
            (cid, uid),
        )
        member = cur.fetchone()

        if not member:
            cur.close()
            conn.close()

            flash("You are not a member of this channel.", "error")
            return redirect(url_for("workspace.workspace_detail", wid=wid))

    cur.execute(
        """
        SELECT u.uid, u.username, u.nickname, u.email, cm.joined_at
        FROM ChannelMembers cm
        JOIN Users u ON cm.uid = u.uid
        WHERE cm.cid = %s
        ORDER BY cm.joined_at ASC
        """,
        (cid,),
    )
    members = cur.fetchall()

    cur.execute(
        """
        SELECT ci.invite_id, u.email, u.username, ci.status, ci.created_at, ci.responded_at
        FROM ChannelInvitations ci
        JOIN Users u ON ci.invitee_uid = u.uid
        WHERE ci.cid = %s
          AND ci.inviter_uid = %s
        ORDER BY ci.created_at DESC
        """,
        (cid, uid),
    )
    sent_invitations = cur.fetchall()

    cur.execute(
        """
        SELECT m.mid, m.content, m.created_at, u.username, u.nickname
        FROM Messages m
        JOIN Users u ON m.sender_id = u.uid
        WHERE m.cid = %s
        ORDER BY m.created_at ASC
        """,
        (cid,),
    )
    messages = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "channel_detail.html",
        channel=channel,
        members=members,
        sent_invitations=sent_invitations,
        messages=messages,
    )


@channel_bp.route("/channels/<int:cid>/invite", methods=["POST"])
def invite_channel_user(cid):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    inviter_uid = session["user_id"]
    invitee_email = request.form["email"]

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT cid, wid, ctype
        FROM Channels
        WHERE cid = %s
        """,
        (cid,),
    )
    channel = cur.fetchone()

    if not channel:
        cur.close()
        conn.close()
        flash("Channel not found.", "error")
        return redirect(url_for("workspace.dashboard"))

    wid = channel[1]
    ctype = channel[2]

    if ctype == "public":
        cur.close()
        conn.close()
        flash("Public channels do not need invitations.", "info")
        return redirect(url_for("channel.channel_detail", cid=cid))

    cur.execute(
        """
        SELECT 1
        FROM ChannelMembers
        WHERE cid = %s AND uid = %s
        """,
        (cid, inviter_uid),
    )
    inviter_is_member = cur.fetchone()

    if not inviter_is_member:
        cur.close()
        conn.close()
        flash("You are not a member of this channel.", "error")
        return redirect(url_for("channel.channel_detail", cid=cid))

    cur.execute(
        """
        SELECT uid
        FROM Users
        WHERE email = %s
        """,
        (invitee_email,),
    )
    invitee = cur.fetchone()

    if not invitee:
        cur.close()
        conn.close()
        flash("User not found.", "error")
        return redirect(url_for("channel.channel_detail", cid=cid))

    invitee_uid = invitee[0]

    cur.execute(
        """
        SELECT 1
        FROM WorkspaceMembership
        WHERE wid = %s AND uid = %s
        """,
        (wid, invitee_uid),
    )
    invitee_in_workspace = cur.fetchone()

    if not invitee_in_workspace:
        cur.close()
        conn.close()
        flash("This user is not a member of this workspace.", "error")
        return redirect(url_for("channel.channel_detail", cid=cid))

    cur.execute(
        """
        SELECT 1
        FROM ChannelMembers
        WHERE cid = %s AND uid = %s
        """,
        (cid, invitee_uid),
    )
    already_member = cur.fetchone()

    if already_member:
        cur.close()
        conn.close()
        flash("This user is already in this channel.", "error")
        return redirect(url_for("channel.channel_detail", cid=cid))

    try:
        if ctype == "direct":
            cur.execute(
                """
                SELECT COUNT(*)
                FROM ChannelMembers
                WHERE cid = %s
                """,
                (cid,),
            )
            member_count = cur.fetchone()[0]

            if member_count >= 2:
                flash("Direct channels can only have two members.", "error")
                conn.rollback()
                return redirect(url_for("channel.channel_detail", cid=cid))

            cur.execute(
                """
                INSERT INTO ChannelMembers (cid, uid)
                VALUES (%s, %s)
                """,
                (cid, invitee_uid),
            )

            cur.execute(
                """
                INSERT INTO ChannelInvitations
                    (
                        cid,
                        inviter_uid,
                        invitee_uid,
                        status,
                        responded_at
                    )
                VALUES (%s, %s, %s, 'accepted', CURRENT_TIMESTAMP)
                """,
                (cid, inviter_uid, invitee_uid),
            )

            conn.commit()
            flash("User added to direct channel.", "success")

        else:
            cur.execute(
                """
                INSERT INTO ChannelInvitations
                    (cid, inviter_uid, invitee_uid, status)
                VALUES (%s, %s, %s, 'pending')
                """,
                (cid, inviter_uid, invitee_uid),
            )

            conn.commit()
            flash("Invitation sent successfully.", "success")

    except Exception as e:
        conn.rollback()
        flash(f"Invite failed: {e}", "error")

    finally:
        cur.close()
        conn.close()

    return redirect(url_for("channel.channel_detail", cid=cid))


@channel_bp.route("/channels/invitations")
def channel_invitations():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    uid = session["user_id"]

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            ci.invite_id,
            c.cname,
            w.wname,
            u.username,
            ci.status,
            ci.created_at,
            ci.responded_at
        FROM ChannelInvitations ci
        JOIN Channels c ON ci.cid = c.cid
        JOIN Workspaces w ON c.wid = w.wid
        JOIN Users u ON ci.inviter_uid = u.uid
        WHERE ci.invitee_uid = %s
        ORDER BY ci.created_at DESC
        """,
        (uid,),
    )

    invitations = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("channel_invitations.html", invitations=invitations)


@channel_bp.route("/channels/invitations/<int:invite_id>/respond", methods=["POST"])
def respond_channel_invitation(invite_id):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    uid = session["user_id"]
    action = request.form["action"]

    if action not in ["accept", "reject"]:
        return "Invalid action."

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT ci.cid, ci.invitee_uid, ci.status, c.wid
        FROM ChannelInvitations ci
        JOIN Channels c ON ci.cid = c.cid
        WHERE ci.invite_id = %s
        """,
        (invite_id,),
    )
    invitation = cur.fetchone()

    if not invitation:
        cur.close()
        conn.close()
        return "Invitation not found."

    cid, invitee_uid, status, wid = invitation

    if invitee_uid != uid:
        cur.close()
        conn.close()
        return "This invitation does not belong to you."

    if status != "pending":
        cur.close()
        conn.close()
        return "This invitation has already been handled."

    try:
        if action == "accept":
            cur.execute(
                """
                INSERT INTO ChannelMembers (cid, uid)
                VALUES (%s, %s)
                """,
                (cid, uid),
            )

            cur.execute(
                """
                UPDATE ChannelInvitations
                SET status = 'accepted',
                    responded_at = CURRENT_TIMESTAMP
                WHERE invite_id = %s
                """,
                (invite_id,),
            )

        else:
            cur.execute(
                """
                UPDATE ChannelInvitations
                SET status = 'rejected',
                    responded_at = CURRENT_TIMESTAMP
                WHERE invite_id = %s
                """,
                (invite_id,),
            )

        conn.commit()

    except Exception as e:
        conn.rollback()
        return f"Respond failed: {e}"

    finally:
        cur.close()
        conn.close()

    return redirect(url_for("channel.channel_invitations"))


@channel_bp.route("/<int:cid>/invitations/sent")
def sent_channel_invitations(cid):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    uid = session["user_id"]

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT cid, cname, wid
        FROM Channels
        WHERE cid = %s
        """,
        (cid,),
    )
    channel = cur.fetchone()

    if not channel:
        cur.close()
        conn.close()
        return "Channel not found."

    cur.execute(
        """
        SELECT 1
        FROM ChannelMembers
        WHERE cid = %s AND uid = %s
        """,
        (cid, uid),
    )
    is_member = cur.fetchone()

    if not is_member:
        cur.close()
        conn.close()
        return "You are not a member of this channel."

    cur.execute(
        """
        SELECT
            ci.invite_id,
            u.email,
            u.username,
            ci.status,
            ci.created_at,
            ci.responded_at
        FROM ChannelInvitations ci
        JOIN Users u ON ci.invitee_uid = u.uid
        WHERE ci.cid = %s
          AND ci.inviter_uid = %s
        ORDER BY ci.created_at DESC
        """,
        (cid, uid),
    )

    invitations = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "sent_channel_invitations.html",
        channel=channel,
        invitations=invitations,
    )
