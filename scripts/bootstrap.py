"""
Script de inicialización segura (Bootstrap).
Genera el administrador por defecto con una contraseña aleatoria.
"""
import os
import sys
import secrets
import string
from dotenv import load_dotenv

# Añadir el directorio src al path para poder importar la app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Cargar variables de entorno
load_dotenv()

from audit_salarial_app import create_app
from audit_salarial_app.extensions import db
from audit_salarial_app.models import Usuario, Rol

app = create_app()

def generar_password(longitud=12):
    alfabeto = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        password = ''.join(secrets.choice(alfabeto) for i in range(longitud))
        if (any(c.islower() for c in password)
                and any(c.isupper() for c in password)
                and sum(c.isdigit() for c in password) >= 1
                and any(c in "!@#$%^&*" for c in password)):
            return password

def init_admin():
    with app.app_context():
        # Asegurarnos de que existe el rol ADMIN
        rol_admin = Rol.query.filter_by(nombre="ADMIN").first()
        if not rol_admin:
            rol_admin = Rol(nombre="ADMIN", descripcion="Administrador del sistema")
            db.session.add(rol_admin)
            db.session.commit()

        # Comprobar si ya hay admin
        admin_existente = Usuario.query.filter_by(email="admin@admin.com").first()
        if admin_existente:
            db.session.delete(admin_existente)
            db.session.commit()
            print("Se ha eliminado el administrador existente para regenerar uno nuevo.")

        password = generar_password()
        
        admin = Usuario(
            email="admin@admin.com",
            nombre="Administrador",
            rol_id=rol_admin.id,
            activo=True,
            must_change_password=True,
            password_hash="tmp"
        )
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()

        print("=" * 50)
        print("ADMINISTRADOR CREADO CON EXITO")
        print(f"Email: admin@admin.com")
        print(f"Password temporal: {password}")
        print("GUARDA ESTA CONTRASEÑA AHORA. Solo se mostrara una vez.")
        print("Deberas cambiarla obligatoriamente en tu primer inicio de sesion.")
        print("=" * 50)

if __name__ == "__main__":
    init_admin()
