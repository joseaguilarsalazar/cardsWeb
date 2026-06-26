# Usamos una imagen ligera oficial de Python
FROM python:3.12-slim

# Evita que Python escriba archivos .pyc en el disco y asegura que los logs salgan directo a la consola
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Establecemos el directorio de trabajo dentro del contenedor
WORKDIR /app

# Instalamos las dependencias del sistema necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiamos e instalamos los requerimientos de Python
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos todo el código fuente del proyecto al contenedor
COPY . /app/

# Otorgamos permisos de ejecución al script de arranque
RUN chmod +x /app/entrypoint.sh

# Exponemos el puerto interno donde escuchará Gunicorn
EXPOSE 8000

# Delegamos el inicio al script de entrada
ENTRYPOINT ["/app/entrypoint.sh"]