import os
import re
import logging
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_file
from flask_login import login_required, current_user

from ..extensions import db
from ..models import Empresa, Usuario, Rol, Auditoria, AuditoriaArchivo, Resultado, Dimension, AuditoriaEvento
from ..auth.decorators import role_required

admin_bp = Blueprint("admin", __name__)

# -------------------------------------------------------
# HELPER: registrar evento en el histórico
# -------------------------------------------------------
def _registrar_evento(auditoria_id, evento, detalle=None,
                      estado_anterior=None, estado_nuevo=None):
    """Inserta una fila en auditoria_evento para trazabilidad."""
    try:
        ev = AuditoriaEvento(
            auditoria_id=auditoria_id,
            usuario_id=current_user.id,
            evento=evento,
            estado_anterior=estado_anterior,
            estado_nuevo=estado_nuevo,
            detalle=detalle,
            ip_origen=request.remote_addr,
        )
        db.session.add(ev)
        db.session.commit()
    except Exception as exc:
        logging.warning(f"No se pudo registrar evento '{evento}': {exc}")

@admin_bp.get("/")
@login_required
def home():
    from sqlalchemy import func
    from ..models import Alerta, Tarea, CitaPlanificada
    from datetime import datetime, date

    rol = current_user.role_name
    empresa_id = current_user.empresa_id

    # --- Base queries filtered by role ---
    aud_q = Auditoria.query
    if rol == 'CLIENTE' and empresa_id:
        aud_q = aud_q.filter_by(empresa_id=empresa_id)
    elif rol == 'AUDITOR':
        aud_q = aud_q.filter_by(auditor_usuario_id=current_user.id)

    # KPI 1: Auditorías activas
    total_auditorias = aud_q.count()
    auditorias_activas = aud_q.filter(Auditoria.estado.in_(['PENDIENTE', 'PROCESANDO', 'REVISION'])).count()

    # KPI 2: Brecha media global
    brecha_q = db.session.query(func.avg(Resultado.brecha_media_pct)).join(Dimension).filter(
        Dimension.codigo == 'GLOBAL', Resultado.brecha_media_pct.isnot(None)
    )
    if rol == 'CLIENTE' and empresa_id:
        brecha_q = brecha_q.join(Auditoria).filter(Auditoria.empresa_id == empresa_id)
    elif rol == 'AUDITOR':
        brecha_q = brecha_q.join(Auditoria).filter(Auditoria.auditor_usuario_id == current_user.id)
    brecha_media_global = brecha_q.scalar() or 0

    # KPI 3: Alertas no leídas
    alerta_q = Alerta.query.filter_by(leida=False)
    if rol == 'CLIENTE' and empresa_id:
        alerta_q = alerta_q.filter_by(usuario_id=current_user.id)
    elif rol == 'AUDITOR':
        alerta_q = alerta_q.join(Auditoria).filter(Auditoria.auditor_usuario_id == current_user.id)
    alertas_pendientes = alerta_q.count()

    # KPI 4: Tareas pendientes
    tarea_q = Tarea.query.filter(Tarea.estado != 'COMPLETADA')
    if rol == 'CLIENTE' and empresa_id:
        tarea_q = tarea_q.join(Auditoria).filter(Auditoria.empresa_id == empresa_id)
    elif rol == 'AUDITOR':
        tarea_q = tarea_q.join(Auditoria).filter(Auditoria.auditor_usuario_id == current_user.id)
    tareas_pendientes = tarea_q.count()

    # Últimas 5 auditorías
    ultimas_auditorias = aud_q.order_by(Auditoria.creada_en.desc()).limit(5).all()

    # Próximas 5 citas
    cita_q = CitaPlanificada.query.filter(CitaPlanificada.fecha_hora >= datetime.utcnow())
    if rol == 'CLIENTE' and empresa_id:
        cita_q = cita_q.join(Auditoria).filter(Auditoria.empresa_id == empresa_id)
    elif rol == 'AUDITOR':
        cita_q = cita_q.join(Auditoria).filter(Auditoria.auditor_usuario_id == current_user.id)
    proximas_citas = cita_q.order_by(CitaPlanificada.fecha_hora.asc()).limit(5).all()

    # Distribución de riesgo
    riesgo_dist_q = db.session.query(
        Resultado.nivel_riesgo, func.count(Resultado.id)
    ).join(Dimension).filter(
        Dimension.codigo == 'GLOBAL', Resultado.nivel_riesgo.isnot(None)
    )
    if rol == 'CLIENTE' and empresa_id:
        riesgo_dist_q = riesgo_dist_q.join(Auditoria).filter(Auditoria.empresa_id == empresa_id)
    elif rol == 'AUDITOR':
        riesgo_dist_q = riesgo_dist_q.join(Auditoria).filter(Auditoria.auditor_usuario_id == current_user.id)
    riesgo_dist = riesgo_dist_q.group_by(Resultado.nivel_riesgo).all()
    riesgo_map = {r[0]: r[1] for r in riesgo_dist}

    # Últimas alertas
    alerta_recientes_q = Alerta.query
    if rol == 'CLIENTE' and empresa_id:
        alerta_recientes_q = alerta_recientes_q.filter_by(usuario_id=current_user.id)
    elif rol == 'AUDITOR':
        alerta_recientes_q = alerta_recientes_q.join(Auditoria).filter(Auditoria.auditor_usuario_id == current_user.id)
    ultimas_alertas = alerta_recientes_q.order_by(Alerta.creada_en.desc()).limit(5).all()

    # Compañías para Cards en Dashboard de ADMIN/AUDITOR
    empresas_cards = []
    if rol in ['ADMIN', 'AUDITOR']:
        if rol == 'ADMIN':
            empresas = Empresa.query.filter_by(activa=True).order_by(Empresa.nombre.asc()).all()
        else:
            empresas = Empresa.query.join(Auditoria).filter(
                Auditoria.auditor_usuario_id == current_user.id,
                Empresa.activa == True
            ).distinct().order_by(Empresa.nombre.asc()).all()

        for emp in empresas:
            total_auds = Auditoria.query.filter_by(empresa_id=emp.id).count()
            active_auds = Auditoria.query.filter_by(empresa_id=emp.id).filter(
                Auditoria.estado.in_(['PENDIENTE', 'PROCESANDO', 'REVISION'])
            ).count()
            brecha_emp = db.session.query(func.avg(Resultado.brecha_media_pct)).join(Dimension).join(Auditoria).filter(
                Auditoria.empresa_id == emp.id,
                Dimension.codigo == 'GLOBAL',
                Resultado.brecha_media_pct.isnot(None)
            ).scalar() or 0

            empresas_cards.append({
                "id": emp.id,
                "nombre": emp.nombre,
                "cif": emp.cif,
                "num_trabajadores": emp.num_trabajadores,
                "total_auditorias": total_auds,
                "auditorias_activas": active_auds,
                "brecha_media": brecha_emp
            })

    return render_template("admin/home.html",
        total_auditorias=total_auditorias,
        auditorias_activas=auditorias_activas,
        brecha_media_global=brecha_media_global,
        alertas_pendientes=alertas_pendientes,
        tareas_pendientes=tareas_pendientes,
        ultimas_auditorias=ultimas_auditorias,
        proximas_citas=proximas_citas,
        riesgo_map=riesgo_map,
        ultimas_alertas=ultimas_alertas,
        empresas_cards=empresas_cards
    )

# -----------------------
# EMPRESAS
# -----------------------
@admin_bp.get("/empresas")
@role_required("ADMIN", "AUDITOR")
def lista_empresas():
    page = request.args.get('page', 1, type=int)
    pagination = Empresa.query.order_by(Empresa.id.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template("admin/lista_empresas.html", pagination=pagination, empresas=pagination.items)

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

@admin_bp.get("/empresas/ver/<int:id>")
@role_required("ADMIN", "AUDITOR")
def empresa_ver(id):
    from sqlalchemy import func
    from ..models import Tarea, CitaPlanificada
    
    emp = db.session.get(Empresa, id)
    if not emp:
        flash("Empresa no encontrada", "error")
        return redirect(url_for("admin.home"))
        
    # If the user is an AUDITOR, verify they are assigned to this company through audits
    if current_user.role_name == 'AUDITOR':
        assigned = Auditoria.query.filter_by(empresa_id=id, auditor_usuario_id=current_user.id).first()
        if not assigned:
            flash("No tienes acceso a esta empresa ya que no eres el auditor asignado a sus auditorías.", "error")
            return redirect(url_for("admin.home"))
            
    # KPIs for this specific company
    total_auditorias = Auditoria.query.filter_by(empresa_id=id).count()
    auditorias_activas = Auditoria.query.filter_by(empresa_id=id).filter(
        Auditoria.estado.in_(['PENDIENTE', 'PROCESANDO', 'REVISION'])
    ).count()
    
    # Brecha media global for this specific company
    brecha_q = db.session.query(func.avg(Resultado.brecha_media_pct)).join(Dimension).join(Auditoria).filter(
        Auditoria.empresa_id == id,
        Dimension.codigo == 'GLOBAL',
        Resultado.brecha_media_pct.isnot(None)
    )
    brecha_media = brecha_q.scalar() or 0
    
    # Audits for this company
    auditorias = Auditoria.query.filter_by(empresa_id=id).order_by(Auditoria.creada_en.desc()).all()
    
    # Tasks for this company's audits
    tareas = Tarea.query.join(Auditoria).filter(Auditoria.empresa_id == id, Tarea.estado != 'COMPLETADA').all()
    
    # Citas for this company's audits
    citas = CitaPlanificada.query.join(Auditoria).filter(Auditoria.empresa_id == id).all()
    
    return render_template("admin/empresa_detalle.html",
        empresa=emp,
        total_auditorias=total_auditorias,
        auditorias_activas=auditorias_activas,
        brecha_media=brecha_media,
        auditorias=auditorias,
        tareas=tareas,
        citas=citas
    )


# -----------------------
# USUARIOS
# -----------------------
@admin_bp.get("/users")
@role_required("ADMIN")
def lista_users():
    page = request.args.get('page', 1, type=int)
    pagination = Usuario.query.order_by(Usuario.id.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template("admin/lista_users.html", pagination=pagination, users=pagination.items)

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
        logging.warning(f"Usuario {u.id} ({u.email}) ha sido desactivado por el ADMIN {current_user.id} ({current_user.email})")
        flash("Usuario desactivado correctamente", "success")
    return redirect(url_for("admin.lista_users"))

@admin_bp.post("/users/activar/<int:id>")
@role_required("ADMIN")
def user_activar(id):
    u = db.session.get(Usuario, id)
    if u:
        u.activo = True
        db.session.commit()
        logging.info(f"Usuario {u.id} ({u.email}) ha sido activado por el ADMIN {current_user.id} ({current_user.email})")
        flash("Usuario activado correctamente", "success")
    return redirect(url_for("admin.lista_users"))

@admin_bp.post("/users/borrar_permanente/<int:id>")
@role_required("ADMIN")
def user_borrar_permanente(id):
    if id == current_user.id:
        flash("No puedes eliminar permanentemente a tu propio usuario", "error")
        return redirect(url_for("admin.lista_users"))

    u = db.session.get(Usuario, id)
    if u:
        if u.activo:
            flash("Solo puedes eliminar permanentemente a usuarios desactivados", "error")
            return redirect(url_for("admin.lista_users"))
        try:
            db.session.delete(u)
            db.session.commit()
            logging.info(f"Usuario {id} ({u.email}) ha sido eliminado permanentemente por el ADMIN {current_user.id} ({current_user.email})")
            flash("Usuario eliminado permanentemente del sistema", "success")
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error al eliminar usuario {id} permanentemente: {e}")
            flash("No se puede eliminar de forma permanente porque tiene auditorías o historial asociado. Puedes mantenerlo desactivado.", "error")
    return redirect(url_for("admin.lista_users"))

# -----------------------
# AUDITORIAS (SUBIDA DE EXCEL Y LISTADO)
# -----------------------
from sqlalchemy import or_, case
from ..models import Resultado

@admin_bp.get("/auditorias")
@login_required
def lista_auditorias():
    q = request.args.get('q', '').strip()
    estado_filtro = request.args.get('estado', '')

    query = db.session.query(Auditoria, Resultado.nivel_riesgo).outerjoin(
        Resultado, 
        (Resultado.auditoria_id == Auditoria.id) & (Resultado.dimension_valor == 'TODOS')
    )

    if current_user.role_name == 'CLIENTE':
        if current_user.empresa_id:
            query = query.filter(Auditoria.empresa_id == current_user.empresa_id)
        else:
            query = query.filter(False)
    elif current_user.role_name == 'AUDITOR':
        # Auditor sees all audits from the company where they are assigned
        # This allows them to see and self-assign to unassigned audits
        if current_user.empresa_id:
            query = query.filter(Auditoria.empresa_id == current_user.empresa_id)
        else:
            # Auditor not assigned to a company sees audits explicitly assigned to them
            from sqlalchemy import select
            empresas_asignadas = select(Auditoria.empresa_id).where(
                Auditoria.auditor_usuario_id == current_user.id
            ).distinct()
            query = query.filter(Auditoria.empresa_id.in_(empresas_asignadas))
            
    if q:
        query = query.join(Empresa).filter(
            or_(
                Empresa.nombre.ilike(f'%{q}%'),
                Empresa.cif.ilike(f'%{q}%')
            )
        )
        
    if estado_filtro:
        query = query.filter(Auditoria.estado == estado_filtro)

    query = query.order_by(
        case(
            (Resultado.nivel_riesgo == 'CRÍTICO', 1),
            (Resultado.nivel_riesgo == 'ALTO', 2),
            (Resultado.nivel_riesgo == 'MEDIO', 3),
            (Resultado.nivel_riesgo == 'BAJO', 4),
            else_=5
        ),
        Auditoria.id.desc()
    )

    page = request.args.get('page', 1, type=int)
    pagination_raw = query.paginate(page=page, per_page=20, error_out=False)
    
    # audits will be a list of objects with a and riesgo attributes for easy templating
    class AuditRow:
        def __init__(self, auditoria, riesgo):
            self.a = auditoria
            self.riesgo = riesgo
            
    audits = [AuditRow(r[0], r[1]) for r in pagination_raw.items]
    
    # Simulate the pagination object but with our custom wrapped items
    class CustomPagination:
        def __init__(self, original_pagination, new_items):
            self.items = new_items
            self.has_prev = original_pagination.has_prev
            self.has_next = original_pagination.has_next
            self.page = original_pagination.page
            self.pages = original_pagination.pages
            self.iter_pages = original_pagination.iter_pages
            self.total = original_pagination.total

    pagination = CustomPagination(pagination_raw, audits)
    
    return render_template(
        "admin/lista_auditorias.html",
        pagination=pagination,
        auditorias=audits,
        q=q,
        estado_filtro=estado_filtro,
    )

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
            
        # Validación de Magic Bytes
        magic_bytes = file.stream.read(8)
        file.stream.seek(0) # Restablecer el puntero de lectura
        
        is_xlsx = magic_bytes.startswith(b'PK\x03\x04')
        is_xls = magic_bytes.startswith(b'\xd0\xcf\x11\xe0')
        
        if not (is_xlsx or is_xls):
            logging.warning(f"Intento de subida de archivo malicioso (Magic Bytes incorrectos) por el usuario {current_user.id}: {file.filename}")
            flash("El archivo no parece ser un documento Excel válido por su estructura interna.", "error")
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

        _registrar_evento(
            a.id,
            evento='SUBIDA_EXCEL',
            detalle=f"Archivo subido: {filename}",
            estado_nuevo='PENDIENTE',
        )
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
        
        estado_prev = auditoria.estado
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
            
        _registrar_evento(
            id,
            evento='CAMBIO_ESTADO',
            detalle=f"Estado actualizado por {current_user.email}",
            estado_anterior=estado_prev,
            estado_nuevo=auditoria.estado,
        )
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
        logging.warning(f"La auditoría {id} ha sido destruida (eliminada permanentemente) por el usuario {current_user.id} ({current_user.email})")
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
    
    # Cargar recomendaciones
    from ..models import AuditoriaRecomendacion
    recomendaciones = AuditoriaRecomendacion.query.filter_by(auditoria_id=id).all()
    
    # Cargar estadísticas sectoriales de la empresa
    from ..models import EstadisticasSectoriales
    est_sector = EstadisticasSectoriales.query.filter_by(sector_id=auditoria.empresa.sector_id).first() if auditoria.empresa and auditoria.empresa.sector_id else None
    
    # Cargar anomalías
    from ..models import Anomalia
    anomalias = Anomalia.query.filter_by(auditoria_id=id).order_by(Anomalia.dimension_valor).all()
    
    return render_template("admin/resultados_auditoria.html", 
                           auditoria=auditoria, 
                           res_global=res_global, 
                           res_grupos=res_grupos,
                           recomendaciones=recomendaciones,
                           est_sector=est_sector,
                           anomalias=anomalias)

@admin_bp.get("/auditorias/<int:id>/anomalia/<int:anomalia_id>/informe")
@login_required
def descargar_informe_individual(id, anomalia_id):
    auditoria = db.session.get(Auditoria, id)
    if not auditoria:
        flash("Auditoría no encontrada", "error")
        return redirect(url_for("admin.lista_auditorias"))
        
    if current_user.role_name == 'CLIENTE' and auditoria.empresa_id != current_user.empresa_id:
        flash("No tienes permiso", "error")
        return redirect(url_for("admin.lista_auditorias"))
        
    from ..services.report_service import generar_informe_individual_pdf
    exito, filepath_or_msg = generar_informe_individual_pdf(id, anomalia_id)
    
    if not exito:
        flash(f"Error al generar informe: {filepath_or_msg}", "error")
        return redirect(url_for("admin.auditoria_resultados", id=id))
        
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filepath_or_msg)
    if not os.path.exists(filepath):
        flash("Error: El archivo PDF no se pudo crear físicamente.", "error")
        return redirect(url_for("admin.auditoria_resultados", id=id))
        
    return send_file(filepath, as_attachment=True, download_name=filepath_or_msg)

# -----------------------
# BLOQUE 4: ESTADÍSTICAS SECTORIALES
# -----------------------
@admin_bp.get("/estadisticas-sectoriales/recalcular")
@login_required
@role_required("ADMIN")
def recalcular_sectoriales():
    from ..models import Sector, EstadisticasSectoriales
    import pandas as pd
    
    # Obtener todos los resultados globales de auditorías completadas
    query = db.session.query(Resultado.brecha_media_pct, Empresa.sector_id).join(
        Auditoria, Auditoria.id == Resultado.auditoria_id
    ).join(
        Empresa, Empresa.id == Auditoria.empresa_id
    ).filter(
        Resultado.dimension_valor == 'TODOS',
        Auditoria.estado == 'COMPLETADA'
    ).all()
    
    if not query:
        flash("No hay suficientes datos para calcular estadísticas.", "warning")
        return redirect(url_for("admin.home"))
        
    df = pd.DataFrame(query, columns=['brecha', 'sector_id'])
    sectores = df.groupby('sector_id').agg(
        brecha_media=('brecha', 'mean'),
        brecha_mediana=('brecha', 'median'),
        n_empresas=('brecha', 'count')
    ).reset_index()
    
    EstadisticasSectoriales.query.delete()
    
    for _, row in sectores.iterrows():
        est = EstadisticasSectoriales(
            sector_id=int(row['sector_id']),
            brecha_media=float(row['brecha_media']),
            brecha_mediana=float(row['brecha_mediana']),
            n_empresas=int(row['n_empresas'])
        )
        db.session.add(est)
        
    db.session.commit()
    flash("Estadísticas sectoriales recalculadas correctamente.", "success")
    return redirect(url_for("admin.home"))

# -----------------------
# BLOQUE 5: EXPORTACIONES
# -----------------------
import io
from flask import send_file

@admin_bp.get("/auditorias/<int:id>/exportar/csv")
@login_required
def exportar_resultados_csv(id):
    auditoria = db.session.get(Auditoria, id)
    if not auditoria or (current_user.role_name == 'CLIENTE' and auditoria.empresa_id != current_user.empresa_id):
        flash("Acceso denegado.", "error")
        return redirect(url_for("admin.lista_auditorias"))
        
    resultados = Resultado.query.filter_by(auditoria_id=id).all()
    
    import csv
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Dimension', 'Valor', 'Hombres', 'Mujeres', 'Media Hombres', 'Media Mujeres', 'Brecha Media %', 'Nivel Riesgo'])
    
    def sanitize_csv(val):
        """Previene CSV Injection prefijando con comilla simple."""
        if val and isinstance(val, str) and val.startswith(('=', '+', '-', '@')):
            return f"'{val}"
        return val

    for r in resultados:
        writer.writerow([
            sanitize_csv(r.dimension.nombre if r.dimension else ''),
            sanitize_csv(r.dimension_valor),
            r.n_hombres,
            r.n_mujeres,
            f"{r.media_hombres:.2f}" if r.media_hombres is not None else "0.00",
            f"{r.media_mujeres:.2f}" if r.media_mujeres is not None else "0.00",
            f"{r.brecha_media_pct:.2f}" if r.brecha_media_pct is not None else "0.00",
            sanitize_csv(r.nivel_riesgo or 'N/D')
        ])
        
    output.seek(0)
    # Convertir a BytesIO para send_file
    mem = io.BytesIO()
    mem.write(output.getvalue().encode('utf-8'))
    mem.seek(0)
    
    return send_file(mem, as_attachment=True, download_name=f'resultados_auditoria_{id}.csv', mimetype='text/csv')


# -----------------------
# BLOQUE 6: CHAT INTERNO
# -----------------------
from flask import jsonify

@admin_bp.route("/auditorias/<int:id>/chat", methods=["GET", "POST"])
@login_required
def auditoria_chat(id):
    """
    GET  → devuelve mensajes JSON (acepta ?after=<id> para polling incremental).
    POST → crea un nuevo mensaje (JSON body: {contenido: "..."}).
    Ambos verifican que el usuario tiene acceso a la auditoría.
    """
    auditoria = db.session.get(Auditoria, id)
    if not auditoria:
        return jsonify({"error": "Auditoría no encontrada"}), 404

    # Verificación de acceso
    rol = current_user.role_name
    if rol == "CLIENTE" and auditoria.empresa_id != current_user.empresa_id:
        return jsonify({"error": "Acceso denegado"}), 403

    from ..models import ChatMensaje
    from ..services.chat_service import crear_mensaje, obtener_mensajes

    if request.method == "GET":
        after_id = request.args.get("after", 0, type=int)
        mensajes = obtener_mensajes(id, after_id=after_id)
        return jsonify([
            {
                "id":        m.id,
                "autor_id":  m.autor_id,
                "autor":     m.autor.nombre,
                "rol":       m.autor.rol.nombre if m.autor.rol else "",
                "contenido": m.contenido,
                "fecha":     m.creado_en.strftime("%d/%m/%Y %H:%M"),
            }
            for m in mensajes
        ])

    # POST
    data = request.get_json(silent=True) or {}
    contenido = (data.get("contenido") or "").strip()
    if not contenido:
        return jsonify({"error": "El mensaje no puede estar vacío"}), 400
    if len(contenido) > 2000:
        return jsonify({"error": "Máximo 2 000 caracteres"}), 400

    try:
        msg = crear_mensaje(id, current_user, contenido)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({
        "id":        msg.id,
        "autor_id":  msg.autor_id,
        "autor":     msg.autor.nombre,
        "rol":       msg.autor.rol.nombre if msg.autor.rol else "",
        "contenido": msg.contenido,
        "fecha":     msg.creado_en.strftime("%d/%m/%Y %H:%M"),
    }), 201

@admin_bp.get("/auditorias/<int:id>/chat/vista")
@login_required
def chat_vista(id):
    auditoria = db.session.get(Auditoria, id)
    if not auditoria:
        flash("Auditoría no encontrada", "error")
        return redirect(url_for("admin.lista_auditorias"))
    if current_user.role_name == 'CLIENTE' and auditoria.empresa_id != current_user.empresa_id:
        flash("Acceso denegado", "error")
        return redirect(url_for("admin.lista_auditorias"))
    return render_template("admin/chat.html", auditoria=auditoria)

# -----------------------
# BLOQUE 7: CALENDARIO + TAREAS + CITAS
# -----------------------
from ..models import Tarea, CitaPlanificada
from datetime import date, timedelta

@admin_bp.get("/calendario")
@login_required
def calendario():
    rol = current_user.role_name
    if rol == 'CLIENTE' and current_user.empresa_id:
        auditorias_list = Auditoria.query.filter_by(empresa_id=current_user.empresa_id).order_by(Auditoria.id.desc()).all()
    elif rol in ('ADMIN',):
        auditorias_list = Auditoria.query.order_by(Auditoria.id.desc()).all()
    else:
        auditorias_list = Auditoria.query.order_by(Auditoria.id.desc()).all()
    return render_template("admin/calendario.html", auditorias=auditorias_list)

@admin_bp.get("/api/eventos")
@login_required
def api_eventos():
    from datetime import datetime as dt
    aid = request.args.get("auditoria_id", type=int)
    rol = current_user.role_name

    tq = Tarea.query.join(Auditoria)
    cq = CitaPlanificada.query.join(Auditoria)

    if rol == 'CLIENTE' and current_user.empresa_id:
        tq = tq.filter(Auditoria.empresa_id == current_user.empresa_id)
        cq = cq.filter(Auditoria.empresa_id == current_user.empresa_id)
    if aid:
        tq = tq.filter(Tarea.auditoria_id == aid)
        cq = cq.filter(CitaPlanificada.auditoria_id == aid)

    color_map = {'TAREA': '#6366f1', 'HITO': '#10b981', 'REUNION': '#f59e0b'}
    eventos = []

    for t in tq.all():
        eventos.append({
            "id": f"tarea-{t.id}",
            "title": t.titulo,
            "start": t.fecha_inicio.isoformat(),
            "end": (t.fecha_fin + timedelta(days=1)).isoformat(),
            "backgroundColor": color_map.get(t.tipo, '#6366f1'),
            "allDay": True,
            "extendedProps": {
                "event_type": "tarea", "db_id": t.id,
                "auditoria_id": t.auditoria_id,
                "empresa": t.auditoria.empresa.nombre if t.auditoria.empresa else "",
                "descripcion": t.descripcion or "",
                "tipo": t.tipo, "prioridad": t.prioridad, "estado": t.estado,
            }
        })

    for c in cq.all():
        eventos.append({
            "id": f"cita-{c.id}",
            "title": f"📌 {c.titulo}",
            "start": c.fecha_hora.isoformat(),
            "backgroundColor": "#ec4899",
            "allDay": False,
            "extendedProps": {
                "event_type": "cita", "db_id": c.id,
                "auditoria_id": c.auditoria_id,
                "empresa": c.auditoria.empresa.nombre if c.auditoria.empresa else "",
                "descripcion": c.descripcion or "",
                "lugar": c.lugar or "", "duracion_min": c.duracion_min,
            }
        })

    return jsonify(eventos)

@admin_bp.route("/tareas", methods=["POST"])
@login_required
def crear_tarea():
    data = request.get_json(silent=True) or {}
    required = ["auditoria_id", "titulo", "fecha_inicio", "fecha_fin"]
    for f in required:
        if not data.get(f):
            return jsonify({"error": f"Campo '{f}' requerido"}), 400
    auditoria = db.session.get(Auditoria, int(data["auditoria_id"]))
    if not auditoria:
        return jsonify({"error": "Auditoría no encontrada"}), 404
    if current_user.role_name == 'CLIENTE' and auditoria.empresa_id != current_user.empresa_id:
        return jsonify({"error": "Acceso denegado"}), 403
    from datetime import datetime as dt
    t = Tarea(
        auditoria_id=auditoria.id, creador_id=current_user.id,
        titulo=data["titulo"].strip(), descripcion=(data.get("descripcion") or "").strip() or None,
        tipo=data.get("tipo", "TAREA"), prioridad=data.get("prioridad", "MEDIA"),
        fecha_inicio=dt.strptime(data["fecha_inicio"], "%Y-%m-%d").date(),
        fecha_fin=dt.strptime(data["fecha_fin"], "%Y-%m-%d").date(),
    )
    db.session.add(t)
    db.session.commit()
    return jsonify({"ok": True, "id": t.id}), 201

@admin_bp.delete("/tareas/<int:id>")
@login_required
def eliminar_tarea(id):
    t = db.session.get(Tarea, id)
    if not t:
        return jsonify({"error": "No encontrada"}), 404
    if current_user.role_name == 'CLIENTE' and t.auditoria.empresa_id != current_user.empresa_id:
        return jsonify({"error": "Acceso denegado"}), 403
    db.session.delete(t)
    db.session.commit()
    return jsonify({"ok": True})

@admin_bp.route("/citas", methods=["POST"])
@login_required
def crear_cita():
    data = request.get_json(silent=True) or {}
    required = ["auditoria_id", "titulo", "fecha_hora"]
    for f in required:
        if not data.get(f):
            return jsonify({"error": f"Campo '{f}' requerido"}), 400
    auditoria = db.session.get(Auditoria, int(data["auditoria_id"]))
    if not auditoria:
        return jsonify({"error": "Auditoría no encontrada"}), 404
    if current_user.role_name == 'CLIENTE' and auditoria.empresa_id != current_user.empresa_id:
        return jsonify({"error": "Acceso denegado"}), 403
    from datetime import datetime as dt
    c = CitaPlanificada(
        auditoria_id=auditoria.id, creador_id=current_user.id,
        titulo=data["titulo"].strip(), descripcion=(data.get("descripcion") or "").strip() or None,
        fecha_hora=dt.fromisoformat(data["fecha_hora"]),
        duracion_min=int(data.get("duracion_min", 60)),
        lugar=(data.get("lugar") or "").strip() or None,
    )
    db.session.add(c)
    db.session.commit()
    return jsonify({"ok": True, "id": c.id}), 201

@admin_bp.delete("/citas/<int:id>")
@login_required
def eliminar_cita(id):
    c = db.session.get(CitaPlanificada, id)
    if not c:
        return jsonify({"error": "No encontrada"}), 404
    if current_user.role_name == 'CLIENTE' and c.auditoria.empresa_id != current_user.empresa_id:
        return jsonify({"error": "Acceso denegado"}), 403
    db.session.delete(c)
    db.session.commit()
    return jsonify({"ok": True})

# -----------------------
# BLOQUE 8: PLAN DE ACTUACIÓN (RD 902/2020)
# -----------------------
from ..models import PlanActuacion, AuditoriaRecomendacion

@admin_bp.route("/auditorias/<int:id>/plan", methods=["GET", "POST"])
@login_required
def plan_actuacion(id):
    auditoria = db.session.get(Auditoria, id)
    if not auditoria:
        flash("Auditoría no encontrada", "error")
        return redirect(url_for("admin.lista_auditorias"))
    if current_user.role_name == 'CLIENTE' and auditoria.empresa_id != current_user.empresa_id:
        flash("Acceso denegado", "error")
        return redirect(url_for("admin.lista_auditorias"))

    plan = PlanActuacion.query.filter_by(auditoria_id=id).first()

    if request.method == "POST":
        if not plan:
            plan = PlanActuacion(auditoria_id=id)
            db.session.add(plan)
        plan.objetivo_general = (request.form.get("objetivo_general") or "").strip() or None
        obj_pct = request.form.get("objetivo_brecha_pct")
        plan.objetivo_brecha_pct = float(obj_pct) if obj_pct else None
        plan.plazo_meses = int(request.form.get("plazo_meses", 12))
        plan.estado = request.form.get("estado", "BORRADOR")
        if plan.estado == 'ACTIVO' and not plan.aprobado_por:
            plan.aprobado_por = current_user.id
            from datetime import datetime as dt
            plan.aprobado_en = dt.utcnow()
        db.session.commit()
        flash("Plan de actuación guardado correctamente", "success")
        return redirect(url_for("admin.plan_actuacion", id=id))

    res_global = Resultado.query.join(Dimension).filter(
        Resultado.auditoria_id == id, Dimension.codigo == 'GLOBAL'
    ).first()
    res_grupos = Resultado.query.join(Dimension).filter(
        Resultado.auditoria_id == id, Dimension.codigo == 'GRUPO_PROFESIONAL'
    ).order_by(Resultado.dimension_valor).all()
    recomendaciones = AuditoriaRecomendacion.query.filter_by(auditoria_id=id).all()
    tareas = Tarea.query.filter_by(auditoria_id=id).order_by(Tarea.fecha_inicio).all()

    return render_template("admin/plan_actuacion.html",
        auditoria=auditoria, plan=plan, res_global=res_global,
        res_grupos=res_grupos, recomendaciones=recomendaciones, tareas=tareas)

@admin_bp.get("/auditorias/<int:id>/plan/exportar")
@login_required
def exportar_plan_pdf(id):
    auditoria = db.session.get(Auditoria, id)
    if not auditoria:
        flash("Auditoría no encontrada", "error")
        return redirect(url_for("admin.lista_auditorias"))
    if current_user.role_name == 'CLIENTE' and auditoria.empresa_id != current_user.empresa_id:
        flash("Acceso denegado", "error")
        return redirect(url_for("admin.lista_auditorias"))
    from ..services.report_service import generar_plan_actuacion_pdf
    exito, resultado = generar_plan_actuacion_pdf(id)
    if not exito:
        flash(f"Error: {resultado}", "error")
        return redirect(url_for("admin.plan_actuacion", id=id))
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], resultado)
    return send_file(filepath, as_attachment=True, download_name=resultado)

# -----------------------
# BLOQUE 9: VALORACIÓN DE PUESTOS (VPT — RD 902/2020, art. 4)
# -----------------------
from ..models import ValoracionPuesto

@admin_bp.route("/auditorias/<int:id>/vpt", methods=["GET", "POST"])
@login_required
def vpt_auditoria(id):
    auditoria = db.session.get(Auditoria, id)
    if not auditoria:
        flash("Auditoría no encontrada", "error")
        return redirect(url_for("admin.lista_auditorias"))
    if current_user.role_name == 'CLIENTE' and auditoria.empresa_id != current_user.empresa_id:
        flash("Acceso denegado", "error")
        return redirect(url_for("admin.lista_auditorias"))

    if request.method == "POST":
        f_form = int(request.form.get("factor_formacion", 5))
        f_cond = int(request.form.get("factor_condiciones", 5))
        f_esf  = int(request.form.get("factor_esfuerzo", 5))
        f_resp = int(request.form.get("factor_responsabilidad", 5))
        puntuacion = round((f_form + f_cond + f_esf + f_resp) / 4 * 10, 2)

        sal_h = request.form.get("salario_medio_h")
        sal_m = request.form.get("salario_medio_m")
        sal_h = float(sal_h) if sal_h else None
        sal_m = float(sal_m) if sal_m else None
        brecha = None
        if sal_h and sal_m and sal_h > 0:
            brecha = round(((sal_h - sal_m) / sal_h) * 100, 3)

        vp = ValoracionPuesto(
            auditoria_id=id,
            nombre_puesto=request.form["nombre_puesto"].strip(),
            grupo_profesional=(request.form.get("grupo_profesional") or "").strip() or None,
            factor_formacion=f_form,
            factor_condiciones=f_cond,
            factor_esfuerzo=f_esf,
            factor_responsabilidad=f_resp,
            puntuacion_total=puntuacion,
            n_ocupantes=int(request.form.get("n_ocupantes", 0)),
            n_hombres=int(request.form.get("n_hombres", 0)),
            n_mujeres=int(request.form.get("n_mujeres", 0)),
            salario_medio_h=sal_h,
            salario_medio_m=sal_m,
            brecha_puesto_pct=brecha,
        )
        db.session.add(vp)
        db.session.commit()
        flash(f"Puesto '{vp.nombre_puesto}' valorado correctamente (puntuación: {puntuacion})", "success")
        return redirect(url_for("admin.vpt_auditoria", id=id))

    puestos = ValoracionPuesto.query.filter_by(auditoria_id=id).order_by(
        ValoracionPuesto.puntuacion_total.desc()
    ).all()

    import json
    puestos_serialized = json.dumps([
        {
            "label": p.nombre_puesto,
            "data": [p.factor_formacion, p.factor_condiciones, p.factor_esfuerzo, p.factor_responsabilidad]
        }
        for p in puestos
    ])

    return render_template("admin/vpt.html", auditoria=auditoria, puestos=puestos, puestos_serialized=puestos_serialized)

@admin_bp.route("/auditorias/<int:id>/vpt/<int:puesto_id>/eliminar", methods=["POST"])
@login_required
def eliminar_vpt(id, puesto_id):
    vp = db.session.get(ValoracionPuesto, puesto_id)
    if not vp or vp.auditoria_id != id:
        flash("Puesto no encontrado", "error")
        return redirect(url_for("admin.vpt_auditoria", id=id))
    db.session.delete(vp)
    db.session.commit()
    flash("Puesto eliminado", "success")
    return redirect(url_for("admin.vpt_auditoria", id=id))


# -----------------------
# BLOQUE 10: PERFIL PROPIO
# -----------------------
@admin_bp.route("/perfil", methods=["GET", "POST"])
@login_required
def perfil():
    if request.method == "POST":
        accion = request.form.get("accion", "datos")

        if accion == "datos":
            nuevo_email = request.form.get("email", "").strip().lower()
            nuevo_nombre = request.form.get("nombre", "").strip()
            nuevos_apellidos = (request.form.get("apellidos") or "").strip() or None

            if not nuevo_email or not nuevo_nombre:
                flash("El nombre y el email son obligatorios.", "error")
                return render_template("admin/perfil.html")

            # Comprobar que el email no lo tiene otro usuario
            conflicto = Usuario.query.filter(
                Usuario.email == nuevo_email,
                Usuario.id != current_user.id
            ).first()
            if conflicto:
                flash("Ese email ya está en uso por otra cuenta.", "error")
                return render_template("admin/perfil.html")

            current_user.email = nuevo_email
            current_user.nombre = nuevo_nombre
            current_user.apellidos = nuevos_apellidos
            db.session.commit()
            flash("Datos actualizados correctamente.", "success")

        elif accion == "password":
            actual = request.form.get("password_actual", "")
            nueva = request.form.get("password_nueva", "")
            confirmar = request.form.get("password_confirmar", "")

            if not current_user.check_password(actual):
                flash("La contraseña actual no es correcta.", "error")
                return render_template("admin/perfil.html")

            if nueva != confirmar:
                flash("La nueva contraseña y su confirmación no coinciden.", "error")
                return render_template("admin/perfil.html")

            if not re.match(
                r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$",
                nueva
            ):
                flash(
                    "La contraseña debe tener al menos 8 caracteres, "
                    "una mayúscula, una minúscula, un número y un carácter especial.",
                    "error",
                )
                return render_template("admin/perfil.html")

            current_user.set_password(nueva)
            current_user.must_change_password = False
            db.session.commit()
            flash("Contraseña cambiada correctamente.", "success")

        return redirect(url_for("admin.perfil"))

    return render_template("admin/perfil.html")


# -----------------------
# BLOQUE 11: DOCUMENTOS ADICIONALES POR AUDITORÍA
# -----------------------
ALLOWED_DOC_EXTENSIONS = {
    "pdf", "doc", "docx", "xls", "xlsx",
    "jpg", "jpeg", "png", "gif",
    "txt", "csv", "zip",
}

def _extension_permitida(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_DOC_EXTENSIONS
    )


@admin_bp.route("/auditorias/<int:id>/documentos", methods=["GET", "POST"])
@login_required
def documentos_auditoria(id):
    auditoria = db.session.get(Auditoria, id)
    if not auditoria:
        flash("Auditoría no encontrada", "error")
        return redirect(url_for("admin.lista_auditorias"))

    # Verificar acceso
    if current_user.role_name == "CLIENTE" and auditoria.empresa_id != current_user.empresa_id:
        flash("Acceso denegado", "error")
        return redirect(url_for("admin.lista_auditorias"))

    if request.method == "POST":
        file = request.files.get("documento")
        descripcion = (request.form.get("descripcion") or "").strip() or None

        if not file or file.filename == "":
            flash("No has seleccionado ningún archivo.", "error")
            return redirect(request.url)

        if not _extension_permitida(file.filename):
            flash(
                f"Tipo de archivo no permitido. Extensiones válidas: "
                f"{', '.join(sorted(ALLOWED_DOC_EXTENSIONS))}",
                "error",
            )
            return redirect(request.url)

        os.makedirs(current_app.config["UPLOAD_FOLDER"], exist_ok=True)
        filename = secure_filename(file.filename)
        # Evitar colisiones de nombre
        from datetime import datetime as _dt
        ts = _dt.now().strftime("%Y%m%d%H%M%S")
        filename = f"{ts}_{filename}"
        filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        doc = AuditoriaArchivo(
            auditoria_id=id,
            tipo="DOCUMENTO_ADICIONAL",
            ruta=filepath,
            nombre=filename,
        )
        # Guardar descripción en el campo nombre visible
        if descripcion:
            doc.nombre = f"{descripcion[:120]} | {filename}"
        db.session.add(doc)
        db.session.commit()

        _registrar_evento(
            id,
            evento="SUBIDA_DOCUMENTO",
            detalle=f"Documento adicional subido: {filename}",
        )
        flash("Documento subido correctamente.", "success")
        return redirect(url_for("admin.documentos_auditoria", id=id))

    # Solo documentos adicionales
    docs = AuditoriaArchivo.query.filter_by(
        auditoria_id=id, tipo="DOCUMENTO_ADICIONAL"
    ).order_by(AuditoriaArchivo.creado_en.desc()).all()

    return render_template("admin/documentos.html", auditoria=auditoria, docs=docs)


@admin_bp.post("/auditorias/<int:id>/documentos/<int:doc_id>/eliminar")
@login_required
def eliminar_documento(id, doc_id):
    doc = db.session.get(AuditoriaArchivo, doc_id)
    if not doc or doc.auditoria_id != id or doc.tipo != "DOCUMENTO_ADICIONAL":
        flash("Documento no encontrado.", "error")
        return redirect(url_for("admin.documentos_auditoria", id=id))

    auditoria = db.session.get(Auditoria, id)
    if current_user.role_name == "CLIENTE" and auditoria.empresa_id != current_user.empresa_id:
        flash("Acceso denegado.", "error")
        return redirect(url_for("admin.documentos_auditoria", id=id))

    # Borrar del disco si existe
    if os.path.exists(doc.ruta):
        try:
            os.remove(doc.ruta)
        except OSError as exc:
            logging.warning(f"No se pudo borrar el archivo físico {doc.ruta}: {exc}")

    _registrar_evento(id, evento="ELIMINACION_DOCUMENTO", detalle=f"Eliminado: {doc.nombre}")
    db.session.delete(doc)
    db.session.commit()
    flash("Documento eliminado.", "success")
    return redirect(url_for("admin.documentos_auditoria", id=id))


# -----------------------
# BLOQUE 12: HISTÓRICO DE ACTIVIDAD
# -----------------------
@admin_bp.get("/auditorias/<int:id>/historico")
@login_required
def historico_auditoria(id):
    auditoria = db.session.get(Auditoria, id)
    if not auditoria:
        flash("Auditoría no encontrada", "error")
        return redirect(url_for("admin.lista_auditorias"))

    if current_user.role_name == "CLIENTE" and auditoria.empresa_id != current_user.empresa_id:
        flash("Acceso denegado", "error")
        return redirect(url_for("admin.lista_auditorias"))

    eventos = (
        AuditoriaEvento.query
        .filter_by(auditoria_id=id)
        .order_by(AuditoriaEvento.creado_en.desc())
        .all()
    )
    # También incluir todos los archivos (Excel + informes + docs adicionales)
    archivos = (
        AuditoriaArchivo.query
        .filter_by(auditoria_id=id)
        .order_by(AuditoriaArchivo.creado_en.desc())
        .all()
    )

    return render_template(
        "admin/historico.html",
        auditoria=auditoria,
        eventos=eventos,
        archivos=archivos,
    )

