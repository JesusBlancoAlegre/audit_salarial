"""
Script para crear/resetear los usuarios de demo en la base de datos.
Ejecutar con: python -m scratch.create_users

Credenciales creadas:
  admin@admin.com     / Admin1234!   (ADMIN)
  auditor@demo.com    / Auditor1!    (AUDITOR)
  cliente@demo.com    / Cliente1!    (CLIENTE - vinculado a Empresa Demo S.L.)
"""
import os
from dotenv import load_dotenv
load_dotenv()

from audit_salarial_app import create_app
from audit_salarial_app.extensions import db
from audit_salarial_app.models import Usuario, Rol, Empresa, Sector

app = create_app()
with app.app_context():
    # ── Roles ──────────────────────────────────────────────────────────────
    roles = {r.nombre: r for r in Rol.query.all()}
    print("Roles disponibles:", list(roles.keys()))

    for nombre_rol in ['ADMIN', 'AUDITOR', 'CLIENTE']:
        if nombre_rol not in roles:
            r = Rol(nombre=nombre_rol, descripcion=nombre_rol.capitalize())
            db.session.add(r)
    db.session.commit()
    roles = {r.nombre: r for r in Rol.query.all()}

    # ── Sector y Empresa de Demo ────────────────────────────────────────────
    sector = Sector.query.first()
    if not sector:
        sector = Sector(codigo='GENERAL', nombre='General / Sin sector específico')
        db.session.add(sector)
        db.session.commit()

    empresa_demo = Empresa.query.filter_by(nombre='Empresa Demo S.L.').first()
    if not empresa_demo:
        empresa_demo = Empresa(
            nombre='Empresa Demo S.L.',
            cif='A12345678',
            num_trabajadores=50,
            email_contacto='contacto@demo.com',
            activa=True
        )
        db.session.add(empresa_demo)
        db.session.commit()
        print(f"Empresa Demo creada (ID={empresa_demo.id})")
    else:
        print(f"Empresa Demo ya existe (ID={empresa_demo.id})")

    # ── Usuarios ────────────────────────────────────────────────────────────
    usuarios_config = [
        {
            'email': 'admin@admin.com',
            'nombre': 'Administrador',
            'apellidos': 'Sistema',
            'rol': 'ADMIN',
            'empresa_id': None,
            'password': 'Admin1234!',
        },
        {
            'email': 'auditor@demo.com',
            'nombre': 'Auditor',
            'apellidos': 'Demo',
            'rol': 'AUDITOR',
            'empresa_id': None,
            'password': 'Auditor1!',
        },
        {
            'email': 'cliente@demo.com',
            'nombre': 'Cliente',
            'apellidos': 'Demo',
            'rol': 'CLIENTE',
            'empresa_id': empresa_demo.id,
            'password': 'Cliente1!',
        },
    ]

    for cfg in usuarios_config:
        u = Usuario.query.filter_by(email=cfg['email']).first()
        if not u:
            u = Usuario(
                email=cfg['email'],
                nombre=cfg['nombre'],
                apellidos=cfg['apellidos'],
                rol_id=roles[cfg['rol']].id,
                empresa_id=cfg['empresa_id'],
                activo=True,
                must_change_password=False,
                password_hash='tmp'
            )
            db.session.add(u)
            db.session.flush()
            u.set_password(cfg['password'])
            print(f"[OK] Creado: {cfg['email']} ({cfg['rol']})")
        else:
            # Reset al estado correcto
            u.activo = True
            u.must_change_password = False
            u.rol_id = roles[cfg['rol']].id
            u.empresa_id = cfg['empresa_id']
            u.set_password(cfg['password'])
            print(f"[>>] Reseteado: {cfg['email']} ({cfg['rol']}) - activo=True, pwd reseteada")

    db.session.commit()

    # ── Resumen ──────────────────────────────────────────────────────────────
    print("\n" + "="*55)
    print("USUARIOS ACTIVOS EN LA BASE DE DATOS:")
    print("="*55)
    for u in Usuario.query.order_by(Usuario.id).all():
        print(f"  ID={u.id:2d}  {u.email:<30s}  [{u.role_name}]  activo={u.activo}")
    print("="*55)
    print("\nCredenciales de acceso:")
    print("  admin@admin.com     / Admin1234!")
    print("  auditor@demo.com    / Auditor1!")
    print("  cliente@demo.com    / Cliente1!")
