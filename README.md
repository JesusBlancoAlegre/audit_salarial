# Audit-Salarial

**Sistema de Auditoría Retributiva y Análisis de Brecha Salarial**

Audit-Salarial es una aplicación web desarrollada en Python (Flask) diseñada para ayudar a las empresas a cumplir con el **Real Decreto 902/2020** de igualdad retributiva entre mujeres y hombres. La plataforma permite la automatización del cálculo de la brecha salarial, la generación de informes oficiales y el análisis demográfico mediante un panel interactivo.

## 🚀 Características Principales

- **Gestión de Roles Segura**: Autenticación para Administradores, Auditores y Clientes utilizando Flask-Login y cifrado de contraseñas (Werkzeug).
- **Procesamiento de Archivos (RAHE)**: Subida y procesamiento automático de plantillas de Excel con Pandas para calcular salarios medios, medianos y la brecha salarial.
- **Generación de Informes**: 
  - Generación de **Informes Técnicos en Word** (`python-docx`) con métricas desglosadas por Grupo Profesional.
  - Generación de **Informes Ejecutivos en PDF** (`reportlab`) inmutables para la dirección.
- **Dashboard Interactivo**: Visualización gráfica de la distribución por géneros y salarios usando `Chart.js`.
- **Protección y Seguridad**: Protección contra ataques CSRF, control dinámico de debug y manejo seguro de variables de entorno (Ocultación de credenciales).

---

## 🛠️ Requisitos del Sistema

- **Python**: 3.10 o superior.
- **Base de datos**: MySQL Server.
- **Dependencias**: Listadas en `requirements.txt` (Flask, Pandas, SQLAlchemy, python-docx, reportlab, etc.)

---

## ⚙️ Instalación y Despliegue Local

Sigue estos pasos para desplegar la aplicación en tu entorno local de desarrollo:

### 1. Clonar el repositorio y preparar el entorno
```bash
# Navega a la carpeta del proyecto
cd src/

# Crea y activa un entorno virtual
python -m venv .venv

# Activar en Windows (PowerShell)
.\.venv\Scripts\activate
# Activar en Linux/Mac
source .venv/bin/activate
```

### 2. Instalar las dependencias
```bash
pip install -r requirements.txt
```

### 3. Configurar la Base de Datos
1. Crea una base de datos en MySQL llamada `audit_salarial`.
2. Las tablas se generan y actualizan mediante migraciones de Flask-Migrate:
   ```bash
   flask db upgrade
   ```
   *(Opcional: Si tienes el script antiguo `audit.sql` o `insertsaudit.sql`, puedes importarlo manualmente, pero se recomiendan las migraciones).*

### 4. Variables de Entorno (.env)
El proyecto utiliza un sistema de variables para no exponer contraseñas.
Renombra o copia el archivo `src/.env.example` a `src/.env` y ajusta los valores obligatorios:
```env
# Clave secreta y base de datos
SECRET_KEY=clave_muy_segura_para_produccion
DATABASE_URL=mysql+pymysql://root:tu_password@localhost:3306/audit_salarial
FLASK_DEBUG=False

# Configuración SMTP para alertas por email (Ejemplo Gmail)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=tu_correo@gmail.com
MAIL_PASSWORD=tu_contraseña_de_aplicacion
```

### 5. Iniciar la aplicación
**Para desarrollo local:**
```bash
python run.py
```
**Para entorno de Producción (Recomendado):**
Utiliza Gunicorn para arrancar la aplicación de forma robusta y concurrente:
```bash
gunicorn -w 4 -b 127.0.0.1:5000 run:app
```
La aplicación estará disponible en tu navegador en la dirección: **http://127.0.0.1:5000**

---

## 👥 Acceso de Prueba (Credenciales por defecto)

Si has importado los datos de prueba (`insertsaudit.sql`), puedes iniciar sesión con:

- **Rol Administrador**:
  - Email: `admin@admin.com`
  - Contraseña: `admin`

---

## 🛡️ Notas de Seguridad
Este proyecto ha sido refactorizado para garantizar un estándar de seguridad:
- Se ha incluido un fichero `.gitignore` para proteger los archivos subidos por clientes (`/uploads`) y prevenir fugas de datos confidenciales (RGPD).
- Todos los formularios cuentan con protección nativa mediante **Tokens CSRF**.

---
*Desarrollado como Trabajo de Fin de Grado (DAM).*
