from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from .extensions import db, login_manager

class Rol(db.Model):
    __tablename__ = "rol"
    id = db.Column(db.SmallInteger, primary_key=True)
    nombre = db.Column(db.String(30), unique=True, nullable=False)
    descripcion = db.Column(db.String(200))

class Empresa(db.Model):
    __tablename__ = "empresa"
    id = db.Column(db.BigInteger, primary_key=True)
    cif = db.Column(db.String(20), unique=True)
    nombre = db.Column(db.String(160), nullable=False)
    num_trabajadores = db.Column(db.Integer, nullable=False, default=0)
    email_contacto = db.Column(db.String(190))
    creada_en = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    activa = db.Column(db.Boolean, nullable=False, default=True)

class Usuario(UserMixin, db.Model):
    __tablename__ = "usuario"
    id = db.Column(db.BigInteger, primary_key=True)

    rol_id = db.Column(db.SmallInteger, db.ForeignKey("rol.id"), nullable=False)
    empresa_id = db.Column(db.BigInteger, db.ForeignKey("empresa.id"))

    email = db.Column(db.String(190), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    nombre = db.Column(db.String(120), nullable=False)
    apellidos = db.Column(db.String(160))
    ultimo_login = db.Column(db.DateTime)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    rol = db.relationship("Rol")
    empresa = db.relationship("Empresa")

    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    @property
    def role_name(self) -> str:
        return self.rol.nombre if self.rol else ""

@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(Usuario, int(user_id))

class Auditoria(db.Model):
    __tablename__ = "auditoria"
    id = db.Column(db.BigInteger, primary_key=True)
    empresa_id = db.Column(db.BigInteger, db.ForeignKey("empresa.id"), nullable=False)
    cliente_usuario_id = db.Column(db.BigInteger, db.ForeignKey("usuario.id"))
    auditor_usuario_id = db.Column(db.BigInteger, db.ForeignKey("usuario.id"))
    
    estado = db.Column(db.String(20), nullable=False, default='PENDIENTE') # Enum mapping
    fecha_periodo_ini = db.Column(db.Date)
    fecha_periodo_fin = db.Column(db.Date)
    creada_en = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    empresa = db.relationship("Empresa")
    cliente = db.relationship("Usuario", foreign_keys=[cliente_usuario_id])
    auditor = db.relationship("Usuario", foreign_keys=[auditor_usuario_id])
    archivos = db.relationship("AuditoriaArchivo", back_populates="auditoria")

class AuditoriaArchivo(db.Model):
    __tablename__ = "auditoria_archivo"
    id = db.Column(db.BigInteger, primary_key=True)
    auditoria_id = db.Column(db.BigInteger, db.ForeignKey("auditoria.id"), nullable=False)
    tipo = db.Column(db.String(30), nullable=False, default='EXCEL_ORIGEN')
    ruta = db.Column(db.String(500), nullable=False)
    nombre = db.Column(db.String(255), nullable=False)
    creado_en = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    auditoria = db.relationship("Auditoria", back_populates="archivos")