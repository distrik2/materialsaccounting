from decimal import Decimal

from datetime import date, timedelta

from flask import Blueprint, jsonify, render_template, request
from flask_login import login_required
from sqlalchemy import func

from ..extensions import db
from ..models import ConstructionObject, Material, Supply, WriteOff
from ..utils import csv_response, paginate

bp = Blueprint("reports", __name__, url_prefix="/reports")


def _parse_date(value: str) -> date | None:
    try:
        v = (value or "").strip()
        if not v:
            return None
        return date.fromisoformat(v)
    except Exception:
        return None


def _date_range(from_date: date, to_date: date):
    cur = from_date
    while cur <= to_date:
        yield cur
        cur = cur + timedelta(days=1)


@bp.route("/dashboard")
@login_required
def dashboard():
    materials_count = db.session.query(func.count(Material.id)).scalar() or 0
    objects_count = db.session.query(func.count(ConstructionObject.id)).scalar() or 0
    supplies_count = db.session.query(func.count(Supply.id)).scalar() or 0
    writeoffs_count = db.session.query(func.count(WriteOff.id)).scalar() or 0

    low_stock = Material.query.order_by(Material.current_stock.asc()).limit(5).all()

    return render_template(
        "reports/dashboard.html",
        materials_count=materials_count,
        objects_count=objects_count,
        supplies_count=supplies_count,
        writeoffs_count=writeoffs_count,
        low_stock=low_stock,
    )


@bp.route("/dashboard/data")
@login_required
def dashboard_data():
    today = date.today()
    date_from = _parse_date(request.args.get("date_from") or "") or (today - timedelta(days=29))
    date_to = _parse_date(request.args.get("date_to") or "") or today

    if date_from > date_to:
        date_from, date_to = date_to, date_from

    supplies_rows = (
        db.session.query(
            Supply.supply_date.label("day"),
            func.coalesce(func.sum(Supply.quantity), 0).label("total_qty"),
        )
        .filter(Supply.supply_date >= date_from)
        .filter(Supply.supply_date <= date_to)
        .group_by(Supply.supply_date)
        .order_by(Supply.supply_date.asc())
        .all()
    )
    writeoffs_rows = (
        db.session.query(
            WriteOff.writeoff_date.label("day"),
            func.coalesce(func.sum(WriteOff.quantity), 0).label("total_qty"),
        )
        .filter(WriteOff.writeoff_date >= date_from)
        .filter(WriteOff.writeoff_date <= date_to)
        .group_by(WriteOff.writeoff_date)
        .order_by(WriteOff.writeoff_date.asc())
        .all()
    )

    supplies_by_day = {r.day: r.total_qty for r in supplies_rows}
    writeoffs_by_day = {r.day: r.total_qty for r in writeoffs_rows}

    labels = [d.isoformat() for d in _date_range(date_from, date_to)]
    supplies_series = [float(supplies_by_day.get(d, 0) or 0) for d in _date_range(date_from, date_to)]
    writeoffs_series = [float(writeoffs_by_day.get(d, 0) or 0) for d in _date_range(date_from, date_to)]

    top_materials = (
        db.session.query(
            Material.name.label("name"),
            Material.unit.label("unit"),
            func.coalesce(func.sum(WriteOff.quantity), 0).label("total_qty"),
        )
        .join(WriteOff, WriteOff.material_id == Material.id)
        .filter(WriteOff.writeoff_date >= date_from)
        .filter(WriteOff.writeoff_date <= date_to)
        .group_by(Material.id, Material.name, Material.unit)
        .order_by(func.sum(WriteOff.quantity).desc())
        .limit(5)
        .all()
    )
    top_objects = (
        db.session.query(
            ConstructionObject.name.label("name"),
            func.coalesce(func.sum(WriteOff.quantity), 0).label("total_qty"),
        )
        .join(WriteOff, WriteOff.object_id == ConstructionObject.id)
        .filter(WriteOff.writeoff_date >= date_from)
        .filter(WriteOff.writeoff_date <= date_to)
        .group_by(ConstructionObject.id, ConstructionObject.name)
        .order_by(func.sum(WriteOff.quantity).desc())
        .limit(5)
        .all()
    )

    unit_for_top_materials = None
    if top_materials:
        unit_for_top_materials = top_materials[0].unit

    return jsonify(
        {
            "range": {"date_from": date_from.isoformat(), "date_to": date_to.isoformat()},
            "by_day": {
                "labels": labels,
                "supplies": supplies_series,
                "writeoffs": writeoffs_series,
            },
            "top_materials": {
                "labels": [r.name for r in top_materials],
                "values": [float(r.total_qty or 0) for r in top_materials],
                "unit": unit_for_top_materials,
            },
            "top_objects": {
                "labels": [r.name for r in top_objects],
                "values": [float(r.total_qty or 0) for r in top_objects],
            },
        }
    )


@bp.route("/stock")
@login_required
def stock_report():
    q = (request.args.get("q") or "").strip()
    query = Material.query

    if q:
        like = f"%{q}%"
        query = query.filter((Material.name.ilike(like)) | (Material.barcode.ilike(like)))

    query = query.order_by(Material.name.asc())

    if (request.args.get("export") or "").lower() == "csv":
        materials = query.all()
        rows = [[m.barcode, m.name, m.unit, f"{m.current_stock:.3f}"] for m in materials]
        return csv_response("stock.csv", ["Штрихкод", "Материал", "Ед.", "Остаток"], rows)

    page = paginate(query, per_page=50)
    return render_template("reports/stock.html", materials=page["items"], page=page, q=q)


@bp.route("/supplies")
@login_required
def supplies_report():
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
            "supplies_report.csv",
            ["Дата", "Штрихкод", "Материал", "Количество", "Ед.", "Примечание"],
            rows,
        )

    page = paginate(query, per_page=50)
    materials = Material.query.order_by(Material.name.asc()).all()

    return render_template(
        "reports/supplies.html",
        supplies=page["items"],
        page=page,
        materials=materials,
        q=q,
        material_id=material_id,
        date_from=request.args.get("date_from") or "",
        date_to=request.args.get("date_to") or "",
    )


@bp.route("/writeoffs")
@login_required
def writeoffs_report():
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
            "writeoffs_report.csv",
            ["Дата", "Объект", "Штрихкод", "Материал", "Количество", "Ед.", "Примечание"],
            rows,
        )

    page = paginate(query, per_page=50)
    materials = Material.query.order_by(Material.name.asc()).all()
    objects = ConstructionObject.query.order_by(ConstructionObject.name.asc()).all()

    return render_template(
        "reports/writeoffs.html",
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


@bp.route("/object-consumption")
@login_required
def object_consumption():
    object_id = (request.args.get("object_id") or "").strip()
    material_id = (request.args.get("material_id") or "").strip()

    rows = (
        db.session.query(
            ConstructionObject.id,
            ConstructionObject.name,
            Material.name.label("material_name"),
            Material.unit,
            func.coalesce(func.sum(WriteOff.quantity), 0).label("total_qty"),
        )
        .join(WriteOff, WriteOff.object_id == ConstructionObject.id)
        .join(Material, Material.id == WriteOff.material_id)
    )

    if object_id:
        try:
            oid = int(object_id)
            rows = rows.filter(ConstructionObject.id == oid)
        except Exception:
            pass
    if material_id:
        try:
            mid = int(material_id)
            rows = rows.filter(Material.id == mid)
        except Exception:
            pass

    rows = (
        rows.group_by(ConstructionObject.id, ConstructionObject.name, Material.name, Material.unit)
        .order_by(ConstructionObject.name.asc(), Material.name.asc())
        .all()
    )

    grouped = {}
    for object_id, object_name, material_name, unit, total_qty in rows:
        grouped.setdefault((object_id, object_name), []).append(
            {
                "material_name": material_name,
                "unit": unit,
                "total_qty": total_qty if total_qty is not None else Decimal("0"),
            }
        )

    if (request.args.get("export") or "").lower() == "csv":
        flat_rows = []
        for (oid, oname), items in grouped.items():
            for it in items:
                flat_rows.append([oname, it["material_name"], f"{it['total_qty']:.3f}", it["unit"]])
        return csv_response(
            "object_consumption.csv",
            ["Объект", "Материал", "Количество", "Ед."],
            flat_rows,
        )

    objects = ConstructionObject.query.order_by(ConstructionObject.name.asc()).all()
    materials = Material.query.order_by(Material.name.asc()).all()

    return render_template(
        "reports/object_consumption.html",
        grouped=grouped,
        objects=objects,
        materials=materials,
        object_id=request.args.get("object_id") or "",
        material_id=request.args.get("material_id") or "",
    )
