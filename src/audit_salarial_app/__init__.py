import logging
from flask import Flask, redirect, url_for
from flask_talisman import Talisman
from .config import Config
from .extensions import db, login_manager, csrf, migrate, limiter, mail

def create_app():
    app = Flask(__name__, template_folder="htmls")
    app.config.from_object(Config)

    # Configuración de Logging de Seguridad
    import os
    from logging.handlers import RotatingFileHandler
    
    # Crear directorio logs si no existe
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, 'audit_security.log')
    handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=10)
    handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] - %(message)s', datefmt="%Y-%m-%d %H:%M:%S"))
    
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)
    mail.init_app(app)
    
    # Configuración de Talisman (Security Headers) con CSP ajustado
    csp = {
        'default-src': [
            '\'self\'',
        ],
        'style-src': [
            '\'self\'',
            '\'unsafe-inline\'',
            'https://fonts.googleapis.com',
            'https://cdn.jsdelivr.net'
        ],
        'script-src': [
            '\'self\'',
            '\'unsafe-inline\'',
            'https://cdn.jsdelivr.net'
        ],
        'font-src': [
            '\'self\'',
            'https://fonts.gstatic.com'
        ]
    }
    Talisman(app, content_security_policy=csp, force_https=False)

    from .models import Alerta
    @app.context_processor
    def inject_alertas():
        from flask_login import current_user
        if current_user.is_authenticated:
            alertas = Alerta.query.filter_by(usuario_id=current_user.id, leida=False).order_by(Alerta.creada_en.desc()).all()
            return dict(alertas_no_leidas=alertas)
        return dict(alertas_no_leidas=[])

    from .auth.routes import auth_bp
    from .admin.routes import admin_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    @app.before_request
    def force_password_change():
        from flask_login import current_user
        from flask import request, redirect, url_for, flash
        
        if current_user.is_authenticated and getattr(current_user, 'must_change_password', False):
            # Exempt routes to avoid redirect loops and allow logging out
            exempt_endpoints = ['admin.perfil', 'auth.logout', 'static']
            if request.endpoint and request.endpoint not in exempt_endpoints:
                flash("Por favor, cambie su contraseña antes de continuar.", "warning")
                return redirect(url_for('admin.perfil'))

    @app.get("/")
    def index():
        return redirect(url_for("auth.login"))

    return app