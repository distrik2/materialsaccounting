from datetime import date

import click
from flask import Flask

from .extensions import db
from .models import User


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
