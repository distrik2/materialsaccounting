from flask import Blueprint, render_template, request
from flask_login import login_required

from ..extensions import db
from ..models import AuditLog, User
from ..security import role_required
from ..utils import paginate

bp = Blueprint("audit", __name__, url_prefix="/audit")


@bp.route("/")
@login_required
@role_required("admin", "manager")
def list_audit():
    q = (request.args.get("q") or "").strip()
    user_id = (request.args.get("user_id") or "").strip()

    query = AuditLog.query

    if q:
        like = f"%{q}%"
        query = query.filter(
            (AuditLog.action.ilike(like))
            | (AuditLog.entity_type.ilike(like))
            | (AuditLog.details.ilike(like))
        )

    if user_id:
        try:
            uid = int(user_id)
            query = query.filter(AuditLog.user_id == uid)
        except Exception:
            pass

    query = query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())

    page = paginate(query, per_page=25)
    users = User.query.order_by(User.username.asc()).all()

    return render_template(
        "audit/list.html",
        logs=page["items"],
        page=page,
        users=users,
        q=q,
        user_id=user_id,
    )
