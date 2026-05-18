import pytest
from audit_salarial_app.models import Usuario, Rol
from audit_salarial_app.extensions import db

def test_registro_crea_usuario_inactivo(client, app):
    # Setup roles
    with app.app_context():
        r = Rol(id=1, nombre="CLIENTE", descripcion="Cliente de prueba")
        db.session.add(r)
        db.session.commit()

    # Intentar registro
    response = client.post("/auth/registrarse", data={
        "email": "test@example.com",
        "nombre": "Test User",
        "password": "StrongPassword123!"
    })

    # El registro debe redirigir al login si es exitoso
    assert response.status_code == 302
    assert "/auth/login" in response.location

    # Verificar que el usuario se creó con activo=False
    with app.app_context():
        user = Usuario.query.filter_by(email="test@example.com").first()
        assert user is not None
        assert user.activo is False
        assert user.must_change_password is False

def test_login_rechaza_usuario_inactivo(client, app):
    # Setup roles y usuario inactivo
    with app.app_context():
        r = Rol(id=1, nombre="CLIENTE", descripcion="Cliente de prueba")
        db.session.add(r)
        db.session.commit()
        
        user = Usuario(email="test@example.com", nombre="Test User", rol_id=r.id, activo=False, password_hash="tmp")
        user.set_password("StrongPassword123!")
        db.session.add(user)
        db.session.commit()

    # Intentar login
    response = client.post("/auth/login", data={
        "email": "test@example.com",
        "password": "StrongPassword123!"
    })

    # Debe rechazar el acceso (403 Forbidden o volver a renderizar login con error)
    assert response.status_code == 403
    assert b"Usuario inactivo" in response.data

def test_must_change_password_redirection(client, app):
    # Setup roles y usuario activo con must_change_password=True
    with app.app_context():
        r = Rol(id=1, nombre="CLIENTE", descripcion="Cliente de prueba")
        db.session.add(r)
        db.session.commit()
        
        user = Usuario(email="test@example.com", nombre="Test User", rol_id=r.id, activo=True, must_change_password=True)
        user.set_password("StrongPassword123!")
        db.session.add(user)
        db.session.commit()

    # Iniciar sesión
    client.post("/auth/login", data={
        "email": "test@example.com",
        "password": "StrongPassword123!"
    })

    # Intentar acceder a admin home
    response = client.get("/admin/")
    
    # Debe redirigir (302) a la página de perfil
    assert response.status_code == 302
    assert "/admin/perfil" in response.location
