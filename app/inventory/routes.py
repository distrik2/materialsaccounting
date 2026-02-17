from datetime import date
from decimal import Decimal

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models import ConstructionObject, Material, Supply, WriteOff
from ..security import role_required

bp = Blueprint("inventory", __name__, url_prefix="/inventory")


def _parse_decimal(value: str) -> Decimal | None:
    try:
        v = (value or "").replace(",", ".").strip()
        if not v:
            return None
        d = Decimal(v)
        return d
    except Exception:
        return None


@bp.route("/supplies")
@login_required
def list_supplies():
    supplies = Supply.query.order_by(Supply.supply_date.desc(), Supply.id.desc()).all()
    return render_template("inventory/supplies_list.html", supplies=supplies)


@bp.route("/supplies/create", methods=["GET", "POST"])
@login_required
@role_required("admin", "storekeeper")
def create_supply():
    materials = Material.query.order_by(Material.name.asc()).all()

    if request.method == "POST":
        material_id = request.form.get("material_id")
        qty = _parse_decimal(request.form.get("quantity") or "")
        supply_date = request.form.get("supply_date")
        note = (request.form.get("note") or "").strip() or None

        material = Material.query.get(material_id) if material_id else None
        if material is None:
            flash("Выберите материал", "danger")
            return render_template("inventory/supply_create.html", materials=materials)

        if qty is None or qty <= 0:
            flash("Количество должно быть больше 0", "danger")
            return render_template("inventory/supply_create.html", materials=materials)

        try:
            dt = date.fromisoformat(supply_date)
        except Exception:
            flash("Некорректная дата поставки", "danger")
            return render_template("inventory/supply_create.html", materials=materials)

        supply = Supply(
            material_id=material.id,
            quantity=qty,
            supply_date=dt,
            note=note,
            created_by=getattr(current_user, "id", None),
        )

        material.current_stock = (material.current_stock or Decimal("0")) + qty
        db.session.add(supply)
        db.session.commit()
        flash("Поставка добавлена", "success")
        return redirect(url_for("inventory.list_supplies"))

    return render_template("inventory/supply_create.html", materials=materials)


@bp.route("/writeoffs")
@login_required
def list_writeoffs():
    writeoffs = WriteOff.query.order_by(WriteOff.writeoff_date.desc(), WriteOff.id.desc()).all()
    return render_template("inventory/writeoffs_list.html", writeoffs=writeoffs)


@bp.route("/writeoffs/create", methods=["GET", "POST"])
@login_required
@role_required("admin", "storekeeper")
def create_writeoff():
    materials = Material.query.order_by(Material.name.asc()).all()
    objects = ConstructionObject.query.order_by(ConstructionObject.name.asc()).all()

    if request.method == "POST":
        material_id = request.form.get("material_id")
        object_id = request.form.get("object_id")
        qty = _parse_decimal(request.form.get("quantity") or "")
        writeoff_date = request.form.get("writeoff_date")
        note = (request.form.get("note") or "").strip() or None

        material = Material.query.get(material_id) if material_id else None
        obj = ConstructionObject.query.get(object_id) if object_id else None

        if material is None:
            flash("Выберите материал", "danger")
            return render_template(
                "inventory/writeoff_create.html", materials=materials, objects=objects
            )
        if obj is None:
            flash("Выберите объект", "danger")
            return render_template(
                "inventory/writeoff_create.html", materials=materials, objects=objects
            )
        if qty is None or qty <= 0:
            flash("Количество должно быть больше 0", "danger")
            return render_template(
                "inventory/writeoff_create.html", materials=materials, objects=objects
            )

        try:
            dt = date.fromisoformat(writeoff_date)
        except Exception:
            flash("Некорректная дата списания", "danger")
            return render_template(
                "inventory/writeoff_create.html", materials=materials, objects=objects
            )

        stock = material.current_stock or Decimal("0")
        if stock < qty:
            flash("Недостаточно остатка на складе", "danger")
            return render_template(
                "inventory/writeoff_create.html", materials=materials, objects=objects
            )

        writeoff = WriteOff(
            material_id=material.id,
            object_id=obj.id,
            quantity=qty,
            writeoff_date=dt,
            note=note,
            created_by=getattr(current_user, "id", None),
        )

        material.current_stock = stock - qty
        db.session.add(writeoff)
        db.session.commit()
        flash("Списание выполнено", "success")
        return redirect(url_for("inventory.list_writeoffs"))

    return render_template("inventory/writeoff_create.html", materials=materials, objects=objects)
