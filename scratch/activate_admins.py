import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
load_dotenv()

from audit_salarial_app import create_app
from audit_salarial_app.extensions import db
from audit_salarial_app.models import Usuario

app = create_app()
with app.app_context():
    admins = Usuario.query.filter_by(rol_id=1).all()
    for admin in admins:
        admin.activo = True
        print(f"Activado admin: {admin.email}")
    db.session.commit()
    print("Base de datos actualizada con éxito.")
