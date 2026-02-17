from decimal import Decimal

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from ..extensions import db
from ..models import Material
from ..security import role_required

bp = Blueprint("materials", __name__, url_prefix="/materials")


@bp.route("/")
@login_required
def list_materials():
    materials = Material.query.order_by(Material.name.asc()).all()
    return render_template("materials/list.html", materials=materials)


@bp.route("/create", methods=["GET", "POST"])
@login_required
@role_required("admin", "storekeeper")
def create_material():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        unit = (request.form.get("unit") or "").strip()

        if not name or not unit:
            flash("Заполните название и единицу измерения", "danger")
            return render_template("materials/create.html")

        existing = Material.query.filter_by(name=name).first()
        if existing is not None:
            flash("Материал с таким названием уже существует", "danger")
            return render_template("materials/create.html")

        m = Material(name=name, unit=unit, current_stock=Decimal("0"))
        db.session.add(m)
        db.session.commit()
        flash("Материал добавлен", "success")
        return redirect(url_for("materials.list_materials"))

    return render_template("materials/create.html")


@bp.route("/<int:material_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("admin", "storekeeper")
def edit_material(material_id: int):
    material = Material.query.get_or_404(material_id)

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        unit = (request.form.get("unit") or "").strip()

        if not name or not unit:
            flash("Заполните название и единицу измерения", "danger")
            return render_template("materials/edit.html", material=material)

        other = Material.query.filter(Material.name == name, Material.id != material.id).first()
        if other is not None:
            flash("Материал с таким названием уже существует", "danger")
            return render_template("materials/edit.html", material=material)

        material.name = name
        material.unit = unit
        db.session.commit()
        flash("Материал обновлен", "success")
        return redirect(url_for("materials.list_materials"))

    return render_template("materials/edit.html", material=material)


@bp.route("/<int:material_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete_material(material_id: int):
    material = Material.query.get_or_404(material_id)

    if material.supplies or material.write_offs:
        flash("Нельзя удалить материал: есть приход или списания", "danger")
        return redirect(url_for("materials.list_materials"))

    db.session.delete(material)
    db.session.commit()
    flash("Материал удален", "success")
    return redirect(url_for("materials.list_materials"))
