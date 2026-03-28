from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class ConstructionObject(db.Model):
    __tablename__ = "objects"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), nullable=False, default="active")


class Material(db.Model):
    __tablename__ = "materials"

    id = db.Column(db.Integer, primary_key=True)
    barcode = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(150), unique=True, nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    current_stock = db.Column(db.Numeric(12, 3), nullable=False, default=Decimal("0"))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class Supply(db.Model):
    __tablename__ = "supplies"

    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey("materials.id"), nullable=False)
    quantity = db.Column(db.Numeric(12, 3), nullable=False)
    supply_date = db.Column(db.Date, nullable=False)
    note = db.Column(db.String(255), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    material = db.relationship("Material", backref=db.backref("supplies", lazy=True))


class WriteOff(db.Model):
    __tablename__ = "write_off"

    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey("materials.id"), nullable=False)
    object_id = db.Column(db.Integer, db.ForeignKey("objects.id"), nullable=False)
    quantity = db.Column(db.Numeric(12, 3), nullable=False)
    writeoff_date = db.Column(db.Date, nullable=False)
    note = db.Column(db.String(255), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    material = db.relationship("Material", backref=db.backref("write_offs", lazy=True))
    object = db.relationship("ConstructionObject", backref=db.backref("write_offs", lazy=True))


class AuditLog(db.Model):
    __tablename__ = "audit_log"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(80), nullable=False)
    entity_type = db.Column(db.String(80), nullable=False)
    entity_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("audit_logs", lazy=True))
