from decimal import Decimal

from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import func

from ..extensions import db
from ..models import ConstructionObject, Material, Supply, WriteOff

bp = Blueprint("reports", __name__, url_prefix="/reports")


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


@bp.route("/stock")
@login_required
def stock_report():
    materials = Material.query.order_by(Material.name.asc()).all()
    return render_template("reports/stock.html", materials=materials)


@bp.route("/supplies")
@login_required
def supplies_report():
    supplies = Supply.query.order_by(Supply.supply_date.desc(), Supply.id.desc()).all()
    return render_template("reports/supplies.html", supplies=supplies)


@bp.route("/writeoffs")
@login_required
def writeoffs_report():
    writeoffs = WriteOff.query.order_by(WriteOff.writeoff_date.desc(), WriteOff.id.desc()).all()
    return render_template("reports/writeoffs.html", writeoffs=writeoffs)


@bp.route("/object-consumption")
@login_required
def object_consumption():
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
        .group_by(ConstructionObject.id, ConstructionObject.name, Material.name, Material.unit)
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

    return render_template("reports/object_consumption.html", grouped=grouped)
