from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from ..audit.service import log_action
from ..extensions import db
from ..models import User
from ..security import role_required

bp = Blueprint("users", __name__, url_prefix="/users")


@bp.route("/")
@login_required
@role_required("admin")
def list_users():
    users = User.query.order_by(User.username.asc()).all()
    return render_template("users/list.html", users=users)


@bp.route("/create", methods=["GET", "POST"])
@login_required
@role_required("admin")
def create_user():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        role = (request.form.get("role") or "").strip()

        if not username or not password or role not in {"admin", "storekeeper", "manager"}:
            flash("Заполните логин/пароль и выберите роль", "danger")
            return render_template("users/create.html")

        existing = User.query.filter_by(username=username).first()
        if existing is not None:
            flash("Пользователь с таким логином уже существует", "danger")
            return render_template("users/create.html")

        user = User(username=username, role=role)
        user.set_password(password)
        db.session.add(user)
        log_action("create_user", "User", None, f"username={username}; role={role}")
        db.session.commit()
        flash("Пользователь создан", "success")
        return redirect(url_for("users.list_users"))

    return render_template("users/create.html")


@bp.route("/<int:user_id>/reset-password", methods=["POST"])
@login_required
@role_required("admin")
def reset_password(user_id: int):
    user = User.query.get_or_404(user_id)
    new_password = request.form.get("new_password") or ""

    if not new_password:
        flash("Введите новый пароль", "danger")
        return redirect(url_for("users.list_users"))

    user.set_password(new_password)
    log_action("reset_password", "User", user.id, f"username={user.username}")
    db.session.commit()
    flash("Пароль обновлен", "success")
    return redirect(url_for("users.list_users"))


@bp.route("/<int:user_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete_user(user_id: int):
    user = User.query.get_or_404(user_id)
    if user.username == "admin":
        flash("Нельзя удалить встроенного администратора", "danger")
        return redirect(url_for("users.list_users"))

    db.session.delete(user)
    log_action("delete_user", "User", user.id, f"username={user.username}")
    db.session.commit()
    flash("Пользователь удален", "success")
    return redirect(url_for("users.list_users"))
