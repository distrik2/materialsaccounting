from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from ..extensions import db
from ..models import ConstructionObject
from ..security import role_required

bp = Blueprint("objects", __name__, url_prefix="/objects")


@bp.route("/")
@login_required
def list_objects():
    objects = ConstructionObject.query.order_by(ConstructionObject.name.asc()).all()
    return render_template("objects/list.html", objects=objects)


@bp.route("/create", methods=["GET", "POST"])
@login_required
@role_required("admin", "storekeeper")
def create_object():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        address = (request.form.get("address") or "").strip()
        status = (request.form.get("status") or "active").strip()

        if not name or not address:
            flash("Заполните название и адрес", "danger")
            return render_template("objects/create.html")

        obj = ConstructionObject(name=name, address=address, status=status or "active")
        db.session.add(obj)
        db.session.commit()
        flash("Объект добавлен", "success")
        return redirect(url_for("objects.list_objects"))

    return render_template("objects/create.html")


@bp.route("/<int:object_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("admin", "storekeeper")
def edit_object(object_id: int):
    obj = ConstructionObject.query.get_or_404(object_id)

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        address = (request.form.get("address") or "").strip()
        status = (request.form.get("status") or "active").strip()

        if not name or not address:
            flash("Заполните название и адрес", "danger")
            return render_template("objects/edit.html", obj=obj)

        obj.name = name
        obj.address = address
        obj.status = status or "active"
        db.session.commit()
        flash("Объект обновлен", "success")
        return redirect(url_for("objects.list_objects"))

    return render_template("objects/edit.html", obj=obj)


@bp.route("/<int:object_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete_object(object_id: int):
    obj = ConstructionObject.query.get_or_404(object_id)

    if obj.write_offs:
        flash("Нельзя удалить объект: есть списания", "danger")
        return redirect(url_for("objects.list_objects"))

    db.session.delete(obj)
    db.session.commit()
    flash("Объект удален", "success")
    return redirect(url_for("objects.list_objects"))
