from flask import Flask, redirect, url_for
from .config import Config
from .extensions import db, login_manager, csrf, migrate

def create_app():
    app = Flask(__name__, template_folder="htmls")
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)

    from .auth.routes import auth_bp
    from .admin.routes import admin_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    @app.get("/")
    def index():
        return redirect(url_for("auth.login"))

    return app