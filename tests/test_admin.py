import pytest
from audit_salarial_app.models import Usuario, Rol, Empresa, Auditoria
from audit_salarial_app.extensions import db

def test_admin_user_deactivation_activation_deletion(client, app):
    with app.app_context():
        # Setup roles
        r_admin = Rol(id=1, nombre="ADMIN", descripcion="Admin")
        r_cliente = Rol(id=3, nombre="CLIENTE", descripcion="Cliente")
        db.session.add_all([r_admin, r_cliente])
        db.session.commit()

        # Create admin and client users
        admin = Usuario(email="admin@example.com", nombre="Admin User", rol_id=r_admin.id, activo=True)
        admin.set_password("AdminPass123!")
        
        client_user = Usuario(email="client@example.com", nombre="Client User", rol_id=r_cliente.id, activo=True)
        client_user.set_password("ClientPass123!")
        
        db.session.add_all([admin, client_user])
        db.session.commit()

    # Log in as admin
    client.post("/auth/login", data={
        "email": "admin@example.com",
        "password": "AdminPass123!"
    })

    # Test Deactivation
    with app.app_context():
        u = Usuario.query.filter_by(email="client@example.com").first()
        client_id = u.id

    # Post to eliminar/deactivate
    response = client.post(f"/admin/users/eliminar/{client_id}")
    assert response.status_code == 302
    
    with app.app_context():
        u = Usuario.query.filter_by(email="client@example.com").first()
        assert u.activo is False

    # Test Activation
    response = client.post(f"/admin/users/activar/{client_id}")
    assert response.status_code == 302
    
    with app.app_context():
        u = Usuario.query.filter_by(email="client@example.com").first()
        assert u.activo is True

    # Deactivate again to allow permanent deletion
    client.post(f"/admin/users/eliminar/{client_id}")

    # Test Permanent Deletion
    response = client.post(f"/admin/users/borrar_permanente/{client_id}")
    assert response.status_code == 302
    
    with app.app_context():
        u = Usuario.query.filter_by(email="client@example.com").first()
        assert u is None

def test_admin_prevent_self_deletion(client, app):
    with app.app_context():
        r_admin = Rol(id=1, nombre="ADMIN", descripcion="Admin")
        db.session.add(r_admin)
        db.session.commit()

        admin = Usuario(email="admin@example.com", nombre="Admin User", rol_id=r_admin.id, activo=True)
        admin.set_password("AdminPass123!")
        db.session.add(admin)
        db.session.commit()
        admin_id = admin.id

    # Log in as admin
    client.post("/auth/login", data={
        "email": "admin@example.com",
        "password": "AdminPass123!"
    })

    # Try to delete self permanent
    response = client.post(f"/admin/users/borrar_permanente/{admin_id}")
    assert response.status_code == 302
    
    with app.app_context():
        u = db.session.get(Usuario, admin_id)
        assert u is not None  # Admin should not be deleted

def test_auditor_multiple_companies_dashboard_and_detail(client, app):
    with app.app_context():
        # Setup roles
        r_admin = Rol(id=1, nombre="ADMIN", descripcion="Admin")
        r_auditor = Rol(id=2, nombre="AUDITOR", descripcion="Auditor")
        r_cliente = Rol(id=3, nombre="CLIENTE", descripcion="Cliente")
        db.session.add_all([r_admin, r_auditor, r_cliente])
        db.session.commit()

        # Create companies
        emp1 = Empresa(id=1, nombre="Empresa Uno", cif="A12345678", activa=True)
        emp2 = Empresa(id=2, nombre="Empresa Dos", cif="B12345678", activa=True)
        emp3 = Empresa(id=3, nombre="Empresa Tres", cif="C12345678", activa=True)
        db.session.add_all([emp1, emp2, emp3])
        db.session.commit()

        # Create users
        admin = Usuario(email="admin@example.com", nombre="Admin User", rol_id=r_admin.id, activo=True)
        admin.set_password("AdminPass123!")
        
        auditor = Usuario(email="auditor@example.com", nombre="Auditor User", rol_id=r_auditor.id, activo=True)
        auditor.set_password("AuditorPass123!")
        
        db.session.add_all([admin, auditor])
        db.session.commit()

        # Assign Auditor to Empresa Uno and Empresa Dos via Auditoria
        aud1 = Auditoria(id=1, empresa_id=emp1.id, auditor_usuario_id=auditor.id, estado='PENDIENTE')
        aud2 = Auditoria(id=2, empresa_id=emp2.id, auditor_usuario_id=auditor.id, estado='PROCESANDO')
        db.session.add_all([aud1, aud2])
        db.session.commit()

    # Log in as AUDITOR
    client.post("/auth/login", data={
        "email": "auditor@example.com",
        "password": "AuditorPass123!"
    })

    # Access main dashboard
    response = client.get("/admin/")
    assert response.status_code == 200
    # Auditor should see their assigned companies
    assert b"Empresa Uno" in response.data
    assert b"Empresa Dos" in response.data
    # Auditor should NOT see Empresa Tres
    assert b"Empresa Tres" not in response.data

    # Auditor accessing detailed view of an assigned company
    response = client.get("/admin/empresas/ver/1")
    assert response.status_code == 200
    assert b"Empresa Uno" in response.data

    # Auditor accessing detailed view of a non-assigned company (should be redirected/blocked)
    response = client.get("/admin/empresas/ver/3")
    assert response.status_code == 302 # Redirect to home
    
    # Log out
    client.get("/auth/logout")

    # Log in as ADMIN
    client.post("/auth/login", data={
        "email": "admin@example.com",
        "password": "AdminPass123!"
    })

    # Access main dashboard
    response = client.get("/admin/")
    assert response.status_code == 200
    # Admin should see ALL companies
    assert b"Empresa Uno" in response.data
    assert b"Empresa Dos" in response.data
    assert b"Empresa Tres" in response.data

    # Admin accessing detailed view of Empresa Tres (should be allowed)
    response = client.get("/admin/empresas/ver/3")
    assert response.status_code == 200
    assert b"Empresa Tres" in response.data

