import os
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_file
from flask_login import login_required, current_user

from ..extensions import db
from ..models import Empresa, Usuario, Rol, Auditoria, AuditoriaArchivo, Resultado, Dimension
from ..auth.decorators import role_required

admin_bp = Blueprint("admin", __name__)

@admin_bp.get("/")
@login_required
def home():
    return render_template("admin/home.html")

# -----------------------
# EMPRESAS
# -----------------------
@admin_bp.get("/empresas")
@role_required("ADMIN", "AUDITOR")
def lista_empresas():
    empresas = Empresa.query.order_by(Empresa.id.desc()).all()
    return render_template("admin/lista_empresas.html", empresas=empresas)

@admin_bp.route("/empresas/nueva", methods=["GET", "POST"])
@role_required("ADMIN")
def empresa_nueva():
    if request.method == "POST":
        emp = Empresa(
            nombre=request.form["nombre"].strip(),
            cif=(request.form.get("cif") or "").strip() or None,
            num_trabajadores=int(request.form.get("num_trabajadores", "0") or 0),
            email_contacto=(request.form.get("email_contacto") or "").strip() or None,
        )
        db.session.add(emp)
        db.session.commit()
        flash("Empresa creada", "success")
        return redirect(url_for("admin.lista_empresas"))

    return render_template("admin/empresa_form.html")

@admin_bp.route("/empresas/editar/<int:id>", methods=["GET", "POST"])
@role_required("ADMIN")
def empresa_editar(id):
    emp = db.session.get(Empresa, id)
    if not emp:
        flash("Empresa no encontrada", "error")
        return redirect(url_for("admin.lista_empresas"))
        
    if request.method == "POST":
        emp.nombre = request.form["nombre"].strip()
        emp.cif = (request.form.get("cif") or "").strip() or None
        emp.num_trabajadores = int(request.form.get("num_trabajadores", "0") or 0)
        emp.email_contacto = (request.form.get("email_contacto") or "").strip() or None
        db.session.commit()
        flash("Empresa actualizada", "success")
        return redirect(url_for("admin.lista_empresas"))
        
    return render_template("admin/empresa_form.html", empresa=emp)

@admin_bp.post("/empresas/eliminar/<int:id>")
@role_required("ADMIN")
def empresa_eliminar(id):
    emp = db.session.get(Empresa, id)
    if emp:
        emp.activa = False
        db.session.commit()
        flash("Empresa desactivada correctamente", "success")
    return redirect(url_for("admin.lista_empresas"))

@admin_bp.post("/empresas/activar/<int:id>")
@role_required("ADMIN")
def empresa_activar(id):
    emp = db.session.get(Empresa, id)
    if emp:
        emp.activa = True
        db.session.commit()
        flash("Empresa reactivada correctamente", "success")
    return redirect(url_for("admin.lista_empresas"))


# -----------------------
# USUARIOS
# -----------------------
@admin_bp.get("/users")
@role_required("ADMIN")
def lista_users():
    users = Usuario.query.order_by(Usuario.id.desc()).all()
    return render_template("admin/lista_users.html", users=users)

@admin_bp.route("/users/nuevo", methods=["GET", "POST"])
@role_required("ADMIN")
def user_nuevo():
    roles = Rol.query.order_by(Rol.nombre.asc()).all()
    empresas = Empresa.query.order_by(Empresa.nombre.asc()).all()

    if request.method == "POST":
        email = request.form["email"].strip().lower()
        if Usuario.query.filter_by(email=email).first():
            flash("Email ya existente", "error")
            return render_template("admin/user_form.html", roles=roles, empresas=empresas), 400

        u = Usuario(
            email=email,
            nombre=request.form["nombre"].strip(),
            apellidos=(request.form.get("apellidos") or "").strip() or None,
            rol_id=int(request.form["rol_id"]),
            empresa_id=int(request.form["empresa_id"]) if request.form.get("empresa_id") else None,
            password_hash="tmp"
        )
        u.set_password(request.form["password"])
        db.session.add(u)
        db.session.commit()

        flash("Usuario creado", "success")
        return redirect(url_for("admin.lista_users"))

    return render_template("admin/user_form.html", roles=roles, empresas=empresas)

@admin_bp.route("/users/editar/<int:id>", methods=["GET", "POST"])
@role_required("ADMIN")
def user_editar(id):
    u = db.session.get(Usuario, id)
    if not u:
        flash("Usuario no encontrado", "error")
        return redirect(url_for("admin.lista_users"))

    roles = Rol.query.order_by(Rol.nombre.asc()).all()
    empresas = Empresa.query.order_by(Empresa.nombre.asc()).all()

    if request.method == "POST":
        u.email = request.form["email"].strip().lower()
        u.nombre = request.form["nombre"].strip()
        u.apellidos = (request.form.get("apellidos") or "").strip() or None
        u.rol_id = int(request.form["rol_id"])
        u.empresa_id = int(request.form["empresa_id"]) if request.form.get("empresa_id") else None
        
        if request.form.get("password"):
            u.set_password(request.form["password"])
            
        db.session.commit()
        flash("Usuario actualizado", "success")
        return redirect(url_for("admin.lista_users"))

    return render_template("admin/user_form.html", roles=roles, empresas=empresas, usuario=u)

@admin_bp.post("/users/eliminar/<int:id>")
@role_required("ADMIN")
def user_eliminar(id):
    u = db.session.get(Usuario, id)
    if u:
        u.activo = False
        db.session.commit()
        flash("Usuario desactivado correctamente", "success")
    return redirect(url_for("admin.lista_users"))

# -----------------------
# AUDITORIAS (SUBIDA DE EXCEL Y LISTADO)
# -----------------------
@admin_bp.get("/auditorias")
@login_required
def lista_auditorias():
    if current_user.role_name == 'CLIENTE':
        if current_user.empresa_id:
            audits = Auditoria.query.filter_by(empresa_id=current_user.empresa_id).order_by(Auditoria.id.desc()).all()
        else:
            audits = []
    else:
        audits = Auditoria.query.order_by(Auditoria.id.desc()).all()
    return render_template("admin/lista_auditorias.html", auditorias=audits)

@admin_bp.route("/auditorias/nueva", methods=["GET", "POST"])
@login_required
def auditoria_nueva():
    if current_user.role_name == 'CLIENTE' and current_user.empresa_id:
        empresas = [current_user.empresa]
    else:
        empresas = Empresa.query.filter_by(activa=True).order_by(Empresa.nombre.asc()).all()
        
    if request.method == "POST":
        file = request.files.get("archivo")
        empresa_id = request.form.get("empresa_id")
        
        if not file or file.filename == "":
            flash("No has seleccionado ningún archivo", "error")
            return redirect(request.url)
            
        if not empresa_id:
            flash("Debes seleccionar la empresa", "error")
            return redirect(request.url)

        if not file.filename.lower().endswith((".xlsx", ".xls")):
            flash("Solo se admiten documentos Excel (.xlsx, .xls)", "error")
            return redirect(request.url)
            
        os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
            
        filename = secure_filename(file.filename)
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        a = Auditoria(
            empresa_id=int(empresa_id),
            cliente_usuario_id=current_user.id if current_user.role_name == 'CLIENTE' else None,
            estado='PENDIENTE'
        )
        db.session.add(a)
        db.session.flush() 
        
        aa = AuditoriaArchivo(
            auditoria_id=a.id,
            tipo='EXCEL_ORIGEN',
            ruta=filepath,
            nombre=filename
        )
        db.session.add(aa)
        db.session.commit()
        
        from ..services.excel_service import procesar_archivo_rahe
        from ..services.brecha_service import calcular_estadisticas

        info_excel = procesar_archivo_rahe(filepath)
        if info_excel["valido"]:
            exito, msg = calcular_estadisticas(a.id, info_excel)
            if exito:
                from ..services.report_service import generar_informe_word, generar_informe_pdf
                generar_informe_word(a.id)
                generar_informe_pdf(a.id)
                
                flash(f"Auditoría iniciada e informes generados. {info_excel['mensaje']}", "success")
            else:
                flash(f"Auditoría creada, pero falló el cálculo: {msg}", "warning")
        else:
            flash(f"Auditoría creada. Falló la lectura interactiva del Excel: {info_excel['mensaje']}", "warning")
        
        return redirect(url_for("admin.lista_auditorias"))
        
    return render_template("admin/auditoria_form.html", empresas=empresas)

@admin_bp.route("/auditorias/editar/<int:id>", methods=["GET", "POST"])
@login_required
@role_required("ADMIN", "AUDITOR")
def auditoria_editar(id):
    auditoria = db.session.get(Auditoria, id)
    if not auditoria:
        flash("Auditoría no encontrada", "error")
        return redirect(url_for("admin.lista_auditorias"))
        
    auditores = Usuario.query.join(Rol).filter(Rol.nombre.in_(['ADMIN', 'AUDITOR'])).all()
        
    if request.method == "POST":
        from datetime import datetime
        
        auditoria.estado = request.form.get("estado")
        auditor_id = request.form.get("auditor_usuario_id")
        auditoria.auditor_usuario_id = int(auditor_id) if auditor_id else None
        
        fechaini_str = request.form.get("fecha_periodo_ini")
        fechafin_str = request.form.get("fecha_periodo_fin")
        
        if fechaini_str:
            auditoria.fecha_periodo_ini = datetime.strptime(fechaini_str, "%Y-%m-%d").date()
        else:
            auditoria.fecha_periodo_ini = None
            
        if fechafin_str:
            auditoria.fecha_periodo_fin = datetime.strptime(fechafin_str, "%Y-%m-%d").date()
        else:
            auditoria.fecha_periodo_fin = None
            
        db.session.commit()
        flash("Auditoría actualizada correctamente", "success")
        return redirect(url_for("admin.lista_auditorias"))
        
    return render_template("admin/auditoria_form_editar.html", auditoria=auditoria, auditores=auditores)

@admin_bp.post("/auditorias/eliminar/<int:id>")
@login_required
@role_required("ADMIN", "AUDITOR")
def auditoria_eliminar(id):
    a = db.session.get(Auditoria, id)
    if a:
        a.estado = 'RECHAZADA'
        db.session.commit()
        flash("La auditoría ha sido rechazada/desactivada.", "success")
    return redirect(url_for("admin.lista_auditorias"))

@admin_bp.post("/auditorias/activar/<int:id>")
@login_required
@role_required("ADMIN", "AUDITOR")
def auditoria_activar(id):
    a = db.session.get(Auditoria, id)
    if a:
        a.estado = 'PENDIENTE'
        db.session.commit()
        flash("La auditoría ha sido reactivada.", "success")
    return redirect(url_for("admin.lista_auditorias"))

@admin_bp.post("/auditorias/destruir/<int:id>")
@login_required
@role_required("ADMIN", "AUDITOR")
def auditoria_destruir(id):
    a = db.session.get(Auditoria, id)
    if a:
        db.session.delete(a)
        db.session.commit()
        flash("La auditoría ha sido eliminada permanentemente de la base de datos.", "success")
    return redirect(url_for("admin.lista_auditorias"))

@admin_bp.get("/archivos/descargar/<int:id>")
@login_required
def descargar_archivo(id):
    archivo = db.session.get(AuditoriaArchivo, id)
    if not archivo:
        flash("Archivo no encontrado", "error")
        return redirect(url_for("admin.lista_auditorias"))
        
    # Validar permisos si es cliente
    if current_user.role_name == 'CLIENTE' and archivo.auditoria.empresa_id != current_user.empresa_id:
        flash("No tienes permiso para descargar este archivo", "error")
        return redirect(url_for("admin.lista_auditorias"))

    # Verifica que el archivo exista en disco
    if not os.path.exists(archivo.ruta):
        flash("El archivo físico ya no se encuentra en el servidor", "error")
        return redirect(url_for("admin.lista_auditorias"))

    return send_file(archivo.ruta, as_attachment=True, download_name=archivo.nombre)

@admin_bp.get("/auditorias/<int:id>/resultados")
@login_required
def auditoria_resultados(id):
    auditoria = db.session.get(Auditoria, id)
    if not auditoria:
        flash("Auditoría no encontrada", "error")
        return redirect(url_for("admin.lista_auditorias"))
        
    # Verificar permisos si es cliente
    if current_user.role_name == 'CLIENTE' and auditoria.empresa_id != current_user.empresa_id:
        flash("No tienes permiso para ver los resultados de esta auditoría", "error")
        return redirect(url_for("admin.lista_auditorias"))
        
    # Cargar resultados
    res_global = Resultado.query.join(Dimension).filter(
        Resultado.auditoria_id == id,
        Dimension.codigo == 'GLOBAL'
    ).first()
    
    res_grupos = Resultado.query.join(Dimension).filter(
        Resultado.auditoria_id == id,
        Dimension.codigo == 'GRUPO_PROFESIONAL'
    ).order_by(Resultado.dimension_valor).all()
    
    return render_template("admin/resultados_auditoria.html", 
                           auditoria=auditoria, 
                           res_global=res_global, 
                           res_grupos=res_grupos)