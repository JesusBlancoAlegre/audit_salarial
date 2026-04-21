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
    telefono_contacto = db.Column(db.String(30))
    direccion = db.Column(db.String(200))
    sector_id = db.Column(db.Integer, db.ForeignKey("sector.id"))
    creada_en = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    activa = db.Column(db.Boolean, nullable=False, default=True)
    
    sector = db.relationship("Sector")

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
    archivos = db.relationship("AuditoriaArchivo", back_populates="auditoria", cascade="all, delete-orphan", passive_deletes=True)

class AuditoriaArchivo(db.Model):
    __tablename__ = "auditoria_archivo"
    id = db.Column(db.BigInteger, primary_key=True)
    auditoria_id = db.Column(db.BigInteger, db.ForeignKey("auditoria.id"), nullable=False)
    tipo = db.Column(db.String(30), nullable=False, default='EXCEL_ORIGEN')
    ruta = db.Column(db.String(500), nullable=False)
    nombre = db.Column(db.String(255), nullable=False)
    creado_en = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    auditoria = db.relationship("Auditoria", back_populates="archivos")

class Sector(db.Model):
    __tablename__ = "sector"
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20))
    nombre = db.Column(db.String(120), nullable=False, unique=True)

class Dimension(db.Model):
    __tablename__ = "dimension"
    id = db.Column(db.SmallInteger, primary_key=True)
    codigo = db.Column(db.String(40), nullable=False, unique=True)
    nombre = db.Column(db.String(80), nullable=False)
    descripcion = db.Column(db.String(255))
    orden = db.Column(db.SmallInteger, default=0)
    activo = db.Column(db.Boolean, nullable=False, default=True)

class AuditoriaEvento(db.Model):
    __tablename__ = "auditoria_evento"
    id = db.Column(db.BigInteger, primary_key=True)
    auditoria_id = db.Column(db.BigInteger, db.ForeignKey("auditoria.id"), nullable=False)
    usuario_id = db.Column(db.BigInteger, db.ForeignKey("usuario.id"))
    evento = db.Column(db.String(60), nullable=False)
    estado_anterior = db.Column(db.String(30))
    estado_nuevo = db.Column(db.String(30))
    detalle = db.Column(db.String(500))
    ip_origen = db.Column(db.String(45))
    creado_en = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    auditoria = db.relationship("Auditoria")
    usuario = db.relationship("Usuario")

class Resultado(db.Model):
    __tablename__ = "resultado"
    id = db.Column(db.BigInteger, primary_key=True)
    auditoria_id = db.Column(db.BigInteger, db.ForeignKey("auditoria.id"), nullable=False)
    dimension_id = db.Column(db.SmallInteger, db.ForeignKey("dimension.id"), nullable=False)
    dimension_valor = db.Column(db.String(140))
    
    n_total = db.Column(db.Integer)
    n_hombres = db.Column(db.Integer)
    n_mujeres = db.Column(db.Integer)
    n_otros = db.Column(db.Integer, default=0)
    
    media_hombres = db.Column(db.Numeric(12, 2))
    media_mujeres = db.Column(db.Numeric(12, 2))
    mediana_hombres = db.Column(db.Numeric(12, 2))
    mediana_mujeres = db.Column(db.Numeric(12, 2))
    salario_minimo = db.Column(db.Numeric(12, 2))
    salario_maximo = db.Column(db.Numeric(12, 2))
    desviacion_tipica = db.Column(db.Numeric(12, 2))
    
    brecha_media_pct = db.Column(db.Numeric(7, 3))
    brecha_mediana_pct = db.Column(db.Numeric(7, 3))
    brecha_media_euros = db.Column(db.Numeric(12, 2))
    
    score_riesgo = db.Column(db.Numeric(6, 3))
    nivel_riesgo = db.Column(db.String(20))
    
    creado_en = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    actualizado_en = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    auditoria = db.relationship("Auditoria")
    dimension = db.relationship("Dimension")

class Anomalia(db.Model):
    __tablename__ = "anomalia"
    id = db.Column(db.BigInteger, primary_key=True)
    auditoria_id = db.Column(db.BigInteger, db.ForeignKey("auditoria.id"), nullable=False)
    dimension_id = db.Column(db.SmallInteger, db.ForeignKey("dimension.id"))
    dimension_valor = db.Column(db.String(140))
    
    metodo = db.Column(db.String(30), nullable=False)
    campo = db.Column(db.String(60), nullable=False)
    valor = db.Column(db.Numeric(12, 2), nullable=False)
    umbral_superior = db.Column(db.Numeric(12, 2))
    umbral_inferior = db.Column(db.Numeric(12, 2))
    z_score = db.Column(db.Numeric(6, 3))
    
    severidad = db.Column(db.String(20), nullable=False, default='MEDIA')
    descripcion = db.Column(db.String(500))
    revisada = db.Column(db.Boolean, nullable=False, default=False)
    revisada_por = db.Column(db.BigInteger)
    
    creado_en = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    auditoria = db.relationship("Auditoria")
    dimension = db.relationship("Dimension")

class RecomendacionCatalogo(db.Model):
    __tablename__ = "recomendacion_catalogo"
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(40), nullable=False, unique=True)
    titulo = db.Column(db.String(160), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    tipo = db.Column(db.String(30), nullable=False, default='OTRA')
    coste_estimado_default = db.Column(db.Numeric(12, 2))
    impacto_default = db.Column(db.Numeric(5, 2))
    meses_default = db.Column(db.SmallInteger)
    activa = db.Column(db.Boolean, nullable=False, default=True)

class AuditoriaRecomendacion(db.Model):
    __tablename__ = "auditoria_recomendacion"
    id = db.Column(db.BigInteger, primary_key=True)
    auditoria_id = db.Column(db.BigInteger, db.ForeignKey("auditoria.id"), nullable=False)
    recomendacion_id = db.Column(db.Integer, db.ForeignKey("recomendacion_catalogo.id"), nullable=False)
    
    prioridad = db.Column(db.String(20), nullable=False, default='MEDIA')
    coste_estimado_eur = db.Column(db.Numeric(14, 2))
    impacto_reduccion_pct = db.Column(db.Numeric(7, 3))
    meses_estimados = db.Column(db.SmallInteger)
    
    aplicada = db.Column(db.Boolean, nullable=False, default=False)
    fecha_aplicacion = db.Column(db.DateTime)
    notas = db.Column(db.String(600))
    
    creado_en = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    auditoria = db.relationship("Auditoria")
    recomendacion = db.relationship("RecomendacionCatalogo")

class EstadisticasSectoriales(db.Model):
    __tablename__ = "estadisticas_sectoriales"
    id = db.Column(db.BigInteger, primary_key=True)
    sector_id = db.Column(db.Integer, db.ForeignKey("sector.id"), nullable=False)
    dimension_id = db.Column(db.SmallInteger, db.ForeignKey("dimension.id"), nullable=False)
    dimension_valor = db.Column(db.String(140))
    anio = db.Column(db.Integer, nullable=False)
    
    n_empresas = db.Column(db.Integer)
    n_empleados_total = db.Column(db.BigInteger)
    
    salario_medio = db.Column(db.Numeric(12, 2))
    salario_p25 = db.Column(db.Numeric(12, 2))
    salario_p50 = db.Column(db.Numeric(12, 2))
    salario_p75 = db.Column(db.Numeric(12, 2))
    
    brecha_media_pct = db.Column(db.Numeric(7, 3))
    brecha_mediana_pct = db.Column(db.Numeric(7, 3))
    brecha_p25_pct = db.Column(db.Numeric(7, 3))
    brecha_p75_pct = db.Column(db.Numeric(7, 3))
    
    percentil_empresa_brecha = db.Column(db.Numeric(5, 2))
    
    actualizado_en = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    sector = db.relationship("Sector")
    dimension = db.relationship("Dimension")

class Alerta(db.Model):
    __tablename__ = "alerta"
    id = db.Column(db.BigInteger, primary_key=True)
    auditoria_id = db.Column(db.BigInteger, db.ForeignKey("auditoria.id"))
    empresa_id = db.Column(db.BigInteger, db.ForeignKey("empresa.id"))
    usuario_id = db.Column(db.BigInteger, db.ForeignKey("usuario.id"))
    
    tipo = db.Column(db.String(40), nullable=False)
    severidad = db.Column(db.String(20), nullable=False, default='INFO')
    canal = db.Column(db.String(20), nullable=False, default='AMBOS')
    asunto = db.Column(db.String(190))
    mensaje = db.Column(db.Text, nullable=False)
    leida = db.Column(db.Boolean, nullable=False, default=False)
    enviada = db.Column(db.Boolean, nullable=False, default=False)
    enviada_en = db.Column(db.DateTime)
    creada_en = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    auditoria = db.relationship("Auditoria")
    empresa = db.relationship("Empresa")
    usuario = db.relationship("Usuario")