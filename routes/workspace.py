from flask import Blueprint, render_template, request, redirect, session, url_for, flash
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


@workspace_bp.route("/create", methods=["POST"])
def create_workspace():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

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
            (wid, uid, "creator"),
        )

        conn.commit()

    except Exception as e:
        conn.rollback()
        return f"Create workspace failed: {e}"

    finally:
        cur.close()
        conn.close()

    return redirect(url_for("workspace.dashboard"))


@workspace_bp.route("/<int:wid>")
def workspace_detail(wid):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    uid = session["user_id"]

    conn = get_db_connection()
    cur = conn.cursor()

    # check membership
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
        flash("You are not a member of this workspace.", "error")
        return redirect(url_for("workspace.dashboard"))

    role = membership[0]

    # workspace info
    cur.execute(
        """
        SELECT wid, wname, description
        FROM Workspaces
        WHERE wid = %s
        """,
        (wid,),
    )
    workspace = cur.fetchone()

    # all public channels and private&direct channels user have joined in this workspace
    cur.execute(
        """
        SELECT DISTINCT c.cid, c.cname, c.ctype, c.created_at
        FROM Channels c
        LEFT JOIN ChannelMembers cm
            ON c.cid = cm.cid
        AND cm.uid = %s
        WHERE c.wid = %s
        AND (
            c.ctype = 'public'
            OR cm.uid IS NOT NULL
        )
        ORDER BY c.created_at DESC
        """,
        (uid, wid),
    )
    channels = cur.fetchall()

    # all workspace members
    cur.execute(
        """
        SELECT u.uid, u.username, u.nickname, u.email, wm.role, wm.joined_at
        FROM WorkspaceMembership wm
        JOIN Users u ON wm.uid = u.uid
        WHERE wm.wid = %s
        ORDER BY wm.role ASC, wm.joined_at ASC
        """,
        (wid,),
    )
    members = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "workspace.html",
        workspace=workspace,
        role=role,
        channels=channels,
        members=members,
    )


@workspace_bp.route("/invitations")
def workspace_invitations():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    uid = session["user_id"]

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            wi.invite_id,
            w.wname,
            u.username,
            wi.status,
            wi.created_at,
            wi.responded_at
        FROM WorkspaceInvitations wi
        JOIN Workspaces w ON wi.wid = w.wid
        JOIN Users u ON wi.inviter_uid = u.uid
        WHERE wi.invitee_uid = %s
        ORDER BY wi.created_at DESC
        """,
        (uid,),
    )

    invitations = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "workspace_invitations.html",
        invitations=invitations,
    )


@workspace_bp.route("/<int:wid>/invite", methods=["POST"])
def invite_user(wid):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    uid = session["user_id"]
    invitee_email = request.form["email"]

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

    if not membership or membership[0] not in ["creator", "admin"]:
        cur.close()
        conn.close()

        flash("Only workspace creator or admins can invite users.", "error")
        return redirect(url_for("workspace.workspace_detail", wid=wid))

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

        flash("User with this email does not exist.", "error")
        return redirect(url_for("workspace.workspace_detail", wid=wid))

    invitee_uid = invitee[0]

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

        flash("This user is already a member.", "warning")
        return redirect(url_for("workspace.workspace_detail", wid=wid))

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

        flash("Invitation sent successfully.", "success")

    except Exception as e:
        conn.rollback()

        flash(f"Invite failed: {e}", "error")

    finally:
        cur.close()
        conn.close()

    return redirect(url_for("workspace.workspace_detail", wid=wid))


@workspace_bp.route("/invitations/<int:invite_id>/respond", methods=["POST"])
def respond_invitation(invite_id):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    uid = session["user_id"]
    action = request.form["action"]

    if action not in ["accept", "reject"]:
        flash("Invalid action.", "error")
        return redirect(url_for("workspace.workspace_invitations"))

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

        flash("Invitation not found.", "error")
        return redirect(url_for("workspace.workspace_invitations"))

    wid, invitee_uid, status = invitation

    if invitee_uid != uid:
        cur.close()
        conn.close()

        flash("This invitation does not belong to you.", "error")
        return redirect(url_for("workspace.workspace_invitations"))

    if status != "pending":
        cur.close()
        conn.close()

        flash("This invitation has already been handled.", "warning")
        return redirect(url_for("workspace.workspace_invitations"))

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

        if action == "accept":
            flash("Invitation accepted successfully.", "success")
        else:
            flash("Invitation rejected.", "info")

    except Exception as e:
        conn.rollback()

        flash(f"Respond invitation failed: {e}", "error")

    finally:
        cur.close()
        conn.close()

    return redirect(url_for("workspace.workspace_invitations"))


@workspace_bp.route("/<int:wid>/invitations/sent")
def sent_workspace_invitations(wid):
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

    if not membership or membership[0] not in ["creator", "admin"]:
        cur.close()
        conn.close()
        flash("Only workspace creator and admins can view invitation history.", "error")
        return redirect(url_for("workspace.workspace_detail", wid=wid))

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

    return render_template(
        "sent_workspace_invitations.html", wid=wid, invitations=invitations
    )


@workspace_bp.route("/<int:wid>/members/<int:target_uid>/promote", methods=["POST"])
def promote_admin(wid, target_uid):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    current_uid = session["user_id"]

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT role
            FROM WorkspaceMembership
            WHERE wid = %s AND uid = %s
            """,
            (wid, current_uid),
        )
        current = cur.fetchone()

        if not current or current[0] != "creator":
            flash("Only the workspace creator can add admins.", "error")
            return redirect(url_for("workspace.workspace_detail", wid=wid))

        cur.execute(
            """
            UPDATE WorkspaceMembership
            SET role = 'admin'
            WHERE wid = %s
              AND uid = %s
              AND role = 'member'
            """,
            (wid, target_uid),
        )

        if cur.rowcount == 0:
            flash("Only regular members can be promoted.", "error")
        else:
            conn.commit()
            flash("User promoted to admin.", "success")

    except Exception as e:
        conn.rollback()
        flash(f"Promote failed: {e}", "error")

    finally:
        cur.close()
        conn.close()

    return redirect(url_for("workspace.workspace_detail", wid=wid))


@workspace_bp.route("/<int:wid>/members/<int:target_uid>/demote", methods=["POST"])
def demote_admin(wid, target_uid):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    current_uid = session["user_id"]

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT role
            FROM WorkspaceMembership
            WHERE wid = %s AND uid = %s
            """,
            (wid, current_uid),
        )
        current = cur.fetchone()

        if not current or current[0] != "creator":
            flash("Only the workspace creator can remove admins.", "error")
            return redirect(url_for("workspace.workspace_detail", wid=wid))

        cur.execute(
            """
            UPDATE WorkspaceMembership
            SET role = 'member'
            WHERE wid = %s
              AND uid = %s
              AND role = 'admin'
            """,
            (wid, target_uid),
        )

        if cur.rowcount == 0:
            flash("Only admins can be demoted.", "error")
        else:
            conn.commit()
            flash("Admin role removed.", "success")

    except Exception as e:
        conn.rollback()
        flash(f"Demote failed: {e}", "error")

    finally:
        cur.close()
        conn.close()

    return redirect(url_for("workspace.workspace_detail", wid=wid))
