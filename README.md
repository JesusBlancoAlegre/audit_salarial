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
2. Importa la estructura de las tablas ejecutando el script proporcionado en la raíz del proyecto:
   ```bash
   mysql -u root -p audit_salarial < ../audit.sql
   mysql -u root -p audit_salarial < ../insertsaudit.sql
   ```

### 4. Variables de Entorno (.env)
El proyecto utiliza un sistema de variables de entorno para no exponer contraseñas en el código.
Renombra o copia el archivo `src/.env.example` a `src/.env` y ajusta los valores:
```env
# Clave secreta de la aplicación (Ejemplo)
SECRET_KEY=clave_muy_segura_para_produccion

# URL de conexión a la base de datos (Usuario, Password, Host, BD)
DATABASE_URL=mysql+pymysql://root:tu_password@localhost:3306/audit_salarial

# Modo Desarrollo (Desactivar en producción)
FLASK_DEBUG=1
```

### 5. Iniciar la aplicación
Una vez configurado todo, levanta el servidor web de Flask:
```bash
python run.py
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
