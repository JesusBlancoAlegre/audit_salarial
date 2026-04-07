from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required

from ..extensions import db
from ..models import Usuario, Rol, Empresa

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        user = Usuario.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash("Credenciales incorrectas", "error")
            return render_template("auth/login.html"), 401

        if not user.activo:
            flash("Usuario inactivo", "error")
            return render_template("auth/login.html"), 403

        user.ultimo_login = datetime.utcnow()
        db.session.commit()

        login_user(user)
        flash("Login correcto", "success")
        return redirect(url_for("admin.home"))

    return render_template("auth/login.html")

@auth_bp.route("/registrarse", methods=["GET", "POST"])
def registrarse():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        nombre = request.form["nombre"].strip()
        password = request.form["password"]

        if Usuario.query.filter_by(email=email).first():
            flash("Ese email ya está registrado", "error")
            return render_template("auth/registrarse.html"), 400

        rol_cliente = Rol.query.filter_by(nombre="CLIENTE").first()
        if not rol_cliente:
            flash("Falta el rol CLIENTE en la tabla rol. Inserta ADMIN/AUDITOR/CLIENTE.", "error")
            return render_template("auth/registrarse.html"), 500

        # Empresa opcional (para ejemplo)
        empresa_nombre = request.form.get("empresa_nombre", "").strip()
        empresa_id = None
        if empresa_nombre:
            emp = Empresa(
                nombre=empresa_nombre,
                num_trabajadores=int(request.form.get("num_trabajadores", "0") or 0),
            )
            db.session.add(emp)
            db.session.flush()
            empresa_id = emp.id

        u = Usuario(
            email=email,
            nombre=nombre,
            rol_id=rol_cliente.id,
            empresa_id=empresa_id,
            password_hash="tmp"
        )
        u.set_password(password)

        db.session.add(u)
        db.session.commit()

        flash("Registro correcto. Ya puedes iniciar sesión.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/registrarse.html")

@auth_bp.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada", "success")
    return redirect(url_for("auth.login"))