from decimal import Decimal

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from ..audit.service import log_action
from ..extensions import db
from ..models import Material
from ..security import role_required

bp = Blueprint("materials", __name__, url_prefix="/materials")


def _safe_next_url(value: str | None) -> str | None:
    v = (value or "").strip()
    if not v:
        return None
    # only allow local relative redirects
    if v.startswith("/"):
        return v
    return None


def _generate_barcode() -> str:
    # Generate a numeric barcode by incrementing the current maximum numeric barcode.
    # Falls back to a stable prefix if there are no numeric barcodes yet.
    max_numeric = None
    for (b,) in db.session.query(Material.barcode).all():
        if b and str(b).isdigit():
            try:
                n = int(b)
            except Exception:
                continue
            if max_numeric is None or n > max_numeric:
                max_numeric = n

    if max_numeric is None:
        return "2000000000001"
    return str(max_numeric + 1)


@bp.route("/")
@login_required
def list_materials():
    materials = Material.query.order_by(Material.name.asc()).all()
    return render_template("materials/list.html", materials=materials)


@bp.route("/create", methods=["GET", "POST"])
@login_required
@role_required("admin", "storekeeper")
def create_material():
    next_url = _safe_next_url(request.args.get("next") or request.form.get("next"))

    if request.method == "POST":
        barcode = (request.form.get("barcode") or "").strip()
        name = (request.form.get("name") or "").strip()
        unit = (request.form.get("unit") or "").strip()

        if not name or not unit:
            flash("Заполните название и единицу измерения", "danger")
            return render_template("materials/create.html", next=next_url)

        if not barcode:
            # Avoid rare collisions by retrying a few times.
            for _ in range(10):
                candidate = _generate_barcode()
                if Material.query.filter_by(barcode=candidate).first() is None:
                    barcode = candidate
                    break
            else:
                flash("Не удалось сгенерировать уникальный штрихкод", "danger")
                return render_template("materials/create.html", next=next_url)

        existing_barcode = Material.query.filter_by(barcode=barcode).first()
        if existing_barcode is not None:
            flash("Материал с таким штрихкодом уже существует", "danger")
            return render_template("materials/create.html", next=next_url)

        existing = Material.query.filter_by(name=name).first()
        if existing is not None:
            flash("Материал с таким названием уже существует", "danger")
            return render_template("materials/create.html", next=next_url)

        m = Material(barcode=barcode, name=name, unit=unit, current_stock=Decimal("0"))
        db.session.add(m)
        log_action("create_material", "Material", None, f"barcode={barcode}; name={name}; unit={unit}")
        db.session.commit()
        flash("Материал добавлен", "success")
        return redirect(next_url or url_for("materials.list_materials"))

    return render_template("materials/create.html", next=next_url)


@bp.route("/<int:material_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("admin", "storekeeper")
def edit_material(material_id: int):
    material = Material.query.get_or_404(material_id)

    if request.method == "POST":
        barcode = (request.form.get("barcode") or "").strip()
        name = (request.form.get("name") or "").strip()
        unit = (request.form.get("unit") or "").strip()

        if not barcode or not name or not unit:
            flash("Заполните штрихкод, название и единицу измерения", "danger")
            return render_template("materials/edit.html", material=material)

        other_barcode = Material.query.filter(
            Material.barcode == barcode,
            Material.id != material.id,
        ).first()
        if other_barcode is not None:
            flash("Материал с таким штрихкодом уже существует", "danger")
            return render_template("materials/edit.html", material=material)

        other = Material.query.filter(Material.name == name, Material.id != material.id).first()
        if other is not None:
            flash("Материал с таким названием уже существует", "danger")
            return render_template("materials/edit.html", material=material)

        material.barcode = barcode
        material.name = name
        material.unit = unit
        log_action("edit_material", "Material", material.id, f"barcode={barcode}; name={name}; unit={unit}")
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
    log_action("delete_material", "Material", material.id, f"barcode={material.barcode}; name={material.name}")
    db.session.commit()
    flash("Материал удален", "success")
    return redirect(url_for("materials.list_materials"))
