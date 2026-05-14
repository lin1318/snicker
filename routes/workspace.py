from flask import Blueprint, render_template, request, redirect, session, url_for
from db import get_db_connection

workspace_bp = Blueprint("workspace", __name__, url_prefix="/workspaces")


@workspace_bp.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    uid = session["user_id"]

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT w.wid, w.wname, w.description, wm.role
        FROM Workspaces w
        JOIN WorkspaceMembership wm ON w.wid = wm.wid
        WHERE wm.uid = %s
        ORDER BY w.created_at DESC
        """,
        (uid,),
    )

    workspaces = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "dashboard.html", username=session["username"], workspaces=workspaces
    )


@workspace_bp.route("/create", methods=["GET", "POST"])
def create_workspace():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        wname = request.form["wname"]
        description = request.form["description"]
        uid = session["user_id"]

        conn = get_db_connection()
        cur = conn.cursor()

        try:
            cur.execute(
                """
                INSERT INTO Workspaces (wname, description, creator_id)
                VALUES (%s, %s, %s)
                RETURNING wid
                """,
                (wname, description, uid),
            )

            wid = cur.fetchone()[0]

            cur.execute(
                """
                INSERT INTO WorkspaceMembership (wid, uid, role)
                VALUES (%s, %s, %s)
                """,
                (wid, uid, "admin"),
            )

            conn.commit()

        except Exception as e:
            conn.rollback()
            return f"Create workspace failed: {e}"

        finally:
            cur.close()
            conn.close()

        return redirect(url_for("workspace.dashboard"))

    return render_template("create_workspace.html")


@workspace_bp.route("/<int:wid>")
def workspace_detail(wid):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    uid = session["user_id"]

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT role
        FROM WorkspaceMembership
        WHERE wid = %s AND uid = %s
        """,
        (wid, uid),
    )

    membership = cur.fetchone()

    if not membership:
        cur.close()
        conn.close()
        return "You are not a member of this workspace."

    role = membership[0]

    cur.execute(
        """
        SELECT wid, wname, description
        FROM Workspaces
        WHERE wid = %s
        """,
        (wid,),
    )

    workspace = cur.fetchone()

    cur.close()
    conn.close()

    return render_template("workspace.html", workspace=workspace, role=role)


@workspace_bp.route("/<int:wid>/invite", methods=["GET", "POST"])
def invite_user(wid):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    uid = session["user_id"]

    conn = get_db_connection()
    cur = conn.cursor()

    # check current user is admin
    cur.execute(
        """
        SELECT role
        FROM WorkspaceMembership
        WHERE wid = %s AND uid = %s
        """,
        (wid, uid),
    )
    membership = cur.fetchone()

    if not membership or membership[0] != "admin":
        cur.close()
        conn.close()
        return render_template(
            "message.html", message="Only workspace admins can invite users."
        )

    if request.method == "POST":
        invitee_email = request.form["email"]

        # find invited user
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
            return render_template(
                "message.html", message="User with this email does not exist."
            )

        invitee_uid = invitee[0]

        # check already member
        cur.execute(
            """
            SELECT 1
            FROM WorkspaceMembership
            WHERE wid = %s AND uid = %s
            """,
            (wid, invitee_uid),
        )
        already_member = cur.fetchone()

        if already_member:
            cur.close()
            conn.close()
            return render_template(
                "message.html", message="This user is already a member."
            )

        # create invitation
        try:
            cur.execute(
                """
                INSERT INTO WorkspaceInvitations
                    (wid, inviter_uid, invitee_uid, status)
                VALUES (%s, %s, %s, 'pending')
                """,
                (wid, uid, invitee_uid),
            )
            conn.commit()

        except Exception as e:
            conn.rollback()
            return f"Invite failed: {e}"

        finally:
            cur.close()
            conn.close()

        return redirect(url_for("workspace.workspace_detail", wid=wid))

    cur.close()
    conn.close()

    return render_template("invite_user.html", wid=wid)


@workspace_bp.route("/invitations")
def workspace_invitations():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    uid = session["user_id"]

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT wi.invite_id, w.wname, u.username, wi.created_at
        FROM WorkspaceInvitations wi
        JOIN Workspaces w ON wi.wid = w.wid
        JOIN Users u ON wi.inviter_uid = u.uid
        WHERE wi.invitee_uid = %s
          AND wi.status = 'pending'
        ORDER BY wi.created_at DESC
        """,
        (uid,),
    )

    invitations = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("workspace_invitations.html", invitations=invitations)


@workspace_bp.route("/invitations/<int:invite_id>/respond", methods=["POST"])
def respond_invitation(invite_id):
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
        SELECT wid, invitee_uid, status
        FROM WorkspaceInvitations
        WHERE invite_id = %s
        """,
        (invite_id,),
    )

    invitation = cur.fetchone()

    if not invitation:
        cur.close()
        conn.close()
        return render_template("message.html", message="Invitation not found.")

    wid, invitee_uid, status = invitation

    if invitee_uid != uid:
        cur.close()
        conn.close()
        return render_template(
            "message.html", message="This invitation does not belong to you."
        )

    if status != "pending":
        cur.close()
        conn.close()
        return render_template(
            "message.html", message="This invitation has already been handled."
        )

    try:
        if action == "accept":
            cur.execute(
                """
                INSERT INTO WorkspaceMembership (wid, uid, role)
                VALUES (%s, %s, 'member')
                """,
                (wid, uid),
            )

            cur.execute(
                """
                UPDATE WorkspaceInvitations
                SET status = 'accepted',
                    responded_at = CURRENT_TIMESTAMP
                WHERE invite_id = %s
                """,
                (invite_id,),
            )

        else:
            cur.execute(
                """
                UPDATE WorkspaceInvitations
                SET status = 'rejected',
                    responded_at = CURRENT_TIMESTAMP
                WHERE invite_id = %s
                """,
                (invite_id,),
            )

        conn.commit()

    except Exception as e:
        conn.rollback()
        return f"Respond invitation failed: {e}"

    finally:
        cur.close()
        conn.close()

    return redirect(url_for("workspace.workspace_invitations"))


@workspace_bp.route("/<int:wid>/invitations/sent")
def sent_invitations(wid):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    uid = session["user_id"]

    conn = get_db_connection()
    cur = conn.cursor()

    # check current user is admin
    cur.execute(
        """
        SELECT role
        FROM WorkspaceMembership
        WHERE wid = %s AND uid = %s
        """,
        (wid, uid),
    )
    membership = cur.fetchone()

    if not membership or membership[0] != "admin":
        cur.close()
        conn.close()
        return render_template(
            "message.html", message="Only workspace admins can view invitation history."
        )

    cur.execute(
        """
        SELECT
            wi.invite_id,
            u.email,
            u.username,
            wi.status,
            wi.created_at,
            wi.responded_at
        FROM WorkspaceInvitations wi
        JOIN Users u ON wi.invitee_uid = u.uid
        WHERE wi.wid = %s
          AND wi.inviter_uid = %s
        ORDER BY wi.created_at DESC
        """,
        (wid, uid),
    )

    invitations = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("sent_invitations.html", wid=wid, invitations=invitations)
