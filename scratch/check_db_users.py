import os
import sys
from dotenv import load_dotenv

# Add src to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

load_dotenv()

from audit_salarial_app import create_app
from audit_salarial_app.extensions import db
from audit_salarial_app.models import Usuario, Rol

app = create_app()
with app.app_context():
    print("ROLES IN DB:")
    for r in Rol.query.all():
        print(f"ID: {r.id}, Nombre: {r.nombre}, Desc: {r.descripcion}")
    
    print("\nUSERS IN DB:")
    for u in Usuario.query.all():
        print(f"ID: {u.id}, Email: {u.email}, Nombre: {u.nombre}, Activo: {u.activo}, Rol ID: {u.rol_id}, Rol: {u.role_name}")
