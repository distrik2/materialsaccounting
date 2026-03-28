from datetime import date, timedelta
from decimal import Decimal
import random

import click
from flask import Flask

from .extensions import db
from .models import ConstructionObject, Material, Supply, User, WriteOff


def init_cli(app: Flask) -> None:
    @app.cli.command("init-db")
    @click.option("--admin-username", default="admin", show_default=True)
    @click.option("--admin-password", default="admin", show_default=True)
    def init_db(admin_username: str, admin_password: str):
        with app.app_context():
            db.create_all()

            existing = User.query.filter_by(username=admin_username).first()
            if existing is None:
                user = User(username=admin_username, role="admin")
                user.set_password(admin_password)
                db.session.add(user)
                db.session.commit()

            return 0

    @app.cli.command("seed")
    @click.option("--force", is_flag=True, help="Пересоздать демо-данные (очистить таблицы).")
    def seed(force: bool):
        with app.app_context():
            db.create_all()

            if force:
                WriteOff.query.delete()
                Supply.query.delete()
                Material.query.delete()
                ConstructionObject.query.delete()
                User.query.filter(User.username != "admin").delete()
                db.session.commit()

            # Ensure demo users
            if User.query.filter_by(username="storekeeper").first() is None:
                u = User(username="storekeeper", role="storekeeper")
                u.set_password("storekeeper")
                db.session.add(u)

            if User.query.filter_by(username="manager").first() is None:
                u = User(username="manager", role="manager")
                u.set_password("manager")
                db.session.add(u)

            db.session.commit()

            if Material.query.count() == 0:
                materials = [
                    ("Цемент М500", "кг"),
                    ("Песок", "т"),
                    ("Щебень", "т"),
                    ("Арматура 12мм", "м"),
                    ("Кирпич", "шт"),
                    ("Плитка", "м2"),
                ]
                for i, (name, unit) in enumerate(materials, start=1):
                    barcode = f"2000000000{i:03d}"
                    db.session.add(
                        Material(barcode=barcode, name=name, unit=unit, current_stock=Decimal("0"))
                    )
                db.session.commit()

            if ConstructionObject.query.count() == 0:
                objects = [
                    ("ЖК Север", "г. Москва, ул. Примерная, 10", "active"),
                    ("Склад на Лесной", "г. Москва, ул. Лесная, 3", "active"),
                    ("Ремонт офиса", "г. Москва, пр-т Мира, 50", "paused"),
                ]
                for name, address, status in objects:
                    db.session.add(ConstructionObject(name=name, address=address, status=status))
                db.session.commit()

            materials = Material.query.order_by(Material.id.asc()).all()
            objects = ConstructionObject.query.order_by(ConstructionObject.id.asc()).all()

            if Supply.query.count() == 0 and WriteOff.query.count() == 0:
                start = date.today() - timedelta(days=30)
                for i in range(18):
                    m = random.choice(materials)
                    qty = Decimal(str(random.choice([10, 25, 50, 75, 100, 150])))
                    dt = start + timedelta(days=random.randint(0, 25))
                    s = Supply(material_id=m.id, quantity=qty, supply_date=dt, note="Демо-поставка")
                    m.current_stock = (m.current_stock or Decimal("0")) + qty
                    db.session.add(s)

                db.session.commit()

                for i in range(22):
                    m = random.choice(materials)
                    o = random.choice(objects)
                    # ensure can writeoff
                    stock = m.current_stock or Decimal("0")
                    if stock <= 0:
                        continue
                    qty = min(stock, Decimal(str(random.choice([5, 10, 15, 20, 30]))))
                    if qty <= 0:
                        continue
                    dt = start + timedelta(days=random.randint(5, 30))
                    w = WriteOff(
                        material_id=m.id,
                        object_id=o.id,
                        quantity=qty,
                        writeoff_date=dt,
                        note="Демо-списание",
                    )
                    m.current_stock = stock - qty
                    db.session.add(w)

                db.session.commit()

            return 0
