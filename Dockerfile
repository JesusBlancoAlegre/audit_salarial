FROM python:3.11-slim

# Evitar que Python escriba archivos .pyc (Punto 2.3)
ENV PYTHONDONTWRITEBYTECODE 1
# Evitar que Python haga buffer de stdout y stderr
ENV PYTHONUNBUFFERED 1

# Crear usuario no root para seguridad
RUN adduser --disabled-password --gecos "" appuser

WORKDIR /app

# Instalar dependencias del sistema necesarias
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        default-libmysqlclient-dev \
        build-essential \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Instalar requerimientos Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el proyecto
COPY . .

# Cambiar permisos
RUN chown -R appuser:appuser /app

# Usar el usuario no root
USER appuser

# Exponer el puerto
EXPOSE 5000

# Comando para ejecutar la aplicación con Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "3", "run:app"]
