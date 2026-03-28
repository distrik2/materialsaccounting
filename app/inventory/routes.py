from datetime import date
from decimal import Decimal

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..audit.service import log_action
from ..extensions import db
from ..models import ConstructionObject, Material, Supply, WriteOff
from ..security import role_required
from ..utils import csv_response, paginate

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


def _parse_date(value: str) -> date | None:
    try:
        v = (value or "").strip()
        if not v:
            return None
        return date.fromisoformat(v)
    except Exception:
        return None


@bp.route("/supplies")
@login_required
def list_supplies():
    q = (request.args.get("q") or "").strip()
    material_id = (request.args.get("material_id") or "").strip()
    date_from = _parse_date(request.args.get("date_from") or "")
    date_to = _parse_date(request.args.get("date_to") or "")

    query = Supply.query.join(Material)

    if q:
        like = f"%{q}%"
        query = query.filter(
            (Material.name.ilike(like)) | (Material.barcode.ilike(like)) | (Supply.note.ilike(like))
        )

    if material_id:
        try:
            mid = int(material_id)
            query = query.filter(Supply.material_id == mid)
        except Exception:
            pass

    if date_from:
        query = query.filter(Supply.supply_date >= date_from)
    if date_to:
        query = query.filter(Supply.supply_date <= date_to)

    query = query.order_by(Supply.supply_date.desc(), Supply.id.desc())

    if (request.args.get("export") or "").lower() == "csv":
        supplies = query.all()
        rows = [
            [
                s.supply_date.isoformat(),
                s.material.barcode,
                s.material.name,
                f"{s.quantity:.3f}",
                s.material.unit,
                s.note or "",
            ]
            for s in supplies
        ]
        return csv_response(
            "supplies.csv",
            ["Дата", "Штрихкод", "Материал", "Количество", "Ед.", "Примечание"],
            rows,
        )

    page = paginate(query, per_page=25)
    materials = Material.query.order_by(Material.name.asc()).all()

    return render_template(
        "inventory/supplies_list.html",
        supplies=page["items"],
        page=page,
        materials=materials,
        q=q,
        material_id=material_id,
        date_from=request.args.get("date_from") or "",
        date_to=request.args.get("date_to") or "",
    )


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

        dt = _parse_date(supply_date)
        if dt is None:
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

        log_action(
            "create_supply",
            "Supply",
            None,
            f"material_id={material.id}; qty={qty}; date={dt.isoformat()}"
            + (f"; note={note}" if note else ""),
        )

        db.session.commit()
        flash("Поставка добавлена", "success")
        return redirect(url_for("inventory.list_supplies"))

    return render_template("inventory/supply_create.html", materials=materials)


@bp.route("/writeoffs")
@login_required
def list_writeoffs():
    q = (request.args.get("q") or "").strip()
    material_id = (request.args.get("material_id") or "").strip()
    object_id = (request.args.get("object_id") or "").strip()
    date_from = _parse_date(request.args.get("date_from") or "")
    date_to = _parse_date(request.args.get("date_to") or "")

    query = WriteOff.query.join(Material).join(ConstructionObject)

    if q:
        like = f"%{q}%"
        query = query.filter(
            (Material.name.ilike(like))
            | (Material.barcode.ilike(like))
            | (ConstructionObject.name.ilike(like))
            | (WriteOff.note.ilike(like))
        )

    if material_id:
        try:
            mid = int(material_id)
            query = query.filter(WriteOff.material_id == mid)
        except Exception:
            pass

    if object_id:
        try:
            oid = int(object_id)
            query = query.filter(WriteOff.object_id == oid)
        except Exception:
            pass

    if date_from:
        query = query.filter(WriteOff.writeoff_date >= date_from)
    if date_to:
        query = query.filter(WriteOff.writeoff_date <= date_to)

    query = query.order_by(WriteOff.writeoff_date.desc(), WriteOff.id.desc())

    if (request.args.get("export") or "").lower() == "csv":
        writeoffs = query.all()
        rows = [
            [
                w.writeoff_date.isoformat(),
                w.object.name,
                w.material.barcode,
                w.material.name,
                f"{w.quantity:.3f}",
                w.material.unit,
                w.note or "",
            ]
            for w in writeoffs
        ]
        return csv_response(
            "writeoffs.csv",
            ["Дата", "Объект", "Штрихкод", "Материал", "Количество", "Ед.", "Примечание"],
            rows,
        )

    page = paginate(query, per_page=25)
    materials = Material.query.order_by(Material.name.asc()).all()
    objects = ConstructionObject.query.order_by(ConstructionObject.name.asc()).all()

    return render_template(
        "inventory/writeoffs_list.html",
        writeoffs=page["items"],
        page=page,
        materials=materials,
        objects=objects,
        q=q,
        material_id=material_id,
        object_id=object_id,
        date_from=request.args.get("date_from") or "",
        date_to=request.args.get("date_to") or "",
    )


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

        dt = _parse_date(writeoff_date)
        if dt is None:
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

        log_action(
            "create_writeoff",
            "WriteOff",
            None,
            f"material_id={material.id}; object_id={obj.id}; qty={qty}; date={dt.isoformat()}"
            + (f"; note={note}" if note else ""),
        )

        db.session.commit()
        flash("Списание выполнено", "success")
        return redirect(url_for("inventory.list_writeoffs"))

    return render_template("inventory/writeoff_create.html", materials=materials, objects=objects)
