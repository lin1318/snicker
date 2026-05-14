from flask import Blueprint, render_template, request, redirect, url_for, session
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
        # check workspace membership
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
            return render_template(
                "message.html", message="You are not a member of this workspace."
            )

        # create channel and get cid
        cur.execute(
            """
            INSERT INTO Channels (wid, cname, ctype, creator_id)
            VALUES (%s, %s, %s, %s)
            RETURNING cid
            """,
            (wid, cname, ctype, uid),
        )

        cid = cur.fetchone()[0]

        # add creator to ChannelMembers
        cur.execute(
            """
            INSERT INTO ChannelMembers (cid, uid)
            VALUES (%s, %s)
            """,
            (cid, uid),
        )

        conn.commit()

    except Exception as e:
        conn.rollback()
        return f"Create channel failed: {e}"

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

    # check user can access this channel
    cur.execute(
        """
        SELECT c.cid, c.cname, c.ctype, c.wid
        FROM Channels c
        JOIN ChannelMembers cm ON c.cid = cm.cid
        WHERE c.cid = %s
          AND cm.uid = %s
        """,
        (cid, uid),
    )
    channel = cur.fetchone()

    if not channel:
        cur.close()
        conn.close()
        return "Channel not found or you do not have access."

    # channel members
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

    # check whether current user is workspace admin
    cur.execute(
        """
        SELECT role
        FROM WorkspaceMembership
        WHERE wid = %s AND uid = %s
        """,
        (channel[3], uid),
    )
    membership = cur.fetchone()
    is_workspace_admin = membership and membership[0] == "admin"

    # sent channel invitations
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

    cur.close()
    conn.close()

    return render_template(
        "channel_detail.html",
        channel=channel,
        members=members,
        is_workspace_admin=is_workspace_admin,
        sent_invitations=sent_invitations,
    )


@channel_bp.route("/workspaces/<int:wid>/channels")
def channel_list(wid):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    uid = session["user_id"]

    conn = get_db_connection()
    cur = conn.cursor()

    # check membership
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
        cur.close()
        conn.close()
        return render_template(
            "message.html", message="You are not a member of this workspace."
        )

    cur.execute(
        """
        SELECT cid, cname, ctype, created_at
        FROM Channels
        WHERE wid = %s
        ORDER BY created_at DESC
        """,
        (wid,),
    )
    channels = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "channels.html",
        wid=wid,
        channels=channels,
    )


@channel_bp.route("/channels/<int:cid>/invite", methods=["POST"])
def invite_channel_user(cid):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    inviter_uid = session["user_id"]
    invitee_email = request.form["email"]

    conn = get_db_connection()
    cur = conn.cursor()

    # get channel and workspace
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
        return "Channel not found."

    wid = channel[1]

    # inviter must be a channel member
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
        return "You are not a member of this channel."

    # find invitee
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
        return "User not found."

    invitee_uid = invitee[0]

    # invitee must already be workspace member
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
        return "This user is not a member of this workspace."

    # check already channel member
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
        return "This user is already in this channel."

    try:
        cur.execute(
            """
            INSERT INTO ChannelInvitations
                (cid, inviter_uid, invitee_uid, status)
            VALUES (%s, %s, %s, 'pending')
            """,
            (cid, inviter_uid, invitee_uid),
        )
        conn.commit()

    except Exception as e:
        conn.rollback()
        return f"Invite failed: {e}"

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
            ci.created_at
        FROM ChannelInvitations ci
        JOIN Channels c ON ci.cid = c.cid
        JOIN Workspaces w ON c.wid = w.wid
        JOIN Users u ON ci.inviter_uid = u.uid
        WHERE ci.invitee_uid = %s
          AND ci.status = 'pending'
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
