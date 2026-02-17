from flask import Flask, redirect, url_for

from .extensions import db, login_manager


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "dev-secret-key"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.sqlite3"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    from .auth.routes import bp as auth_bp
    from .users.routes import bp as users_bp
    from .materials.routes import bp as materials_bp
    from .objects.routes import bp as objects_bp
    from .inventory.routes import bp as inventory_bp
    from .reports.routes import bp as reports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(materials_bp)
    app.register_blueprint(objects_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(reports_bp)

    @app.route("/")
    def index():
        return redirect(url_for("reports.dashboard"))

    from .cli import init_cli

    init_cli(app)

    return app
