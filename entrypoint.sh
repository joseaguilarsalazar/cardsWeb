#!/bin/sh

# Salir inmediatamente si un comando falla
set -e

echo "⏳ Esperando a que la base de datos PostgreSQL esté lista..."
# (El Healthcheck de Docker Compose se encargará de que Postgres esté disponible antes de correr este script)

echo "🚀 Aplicando migraciones de la base de datos..."
python manage.py migrate --noinput

echo "📦 Recopilando archivos estáticos (CSS, JS, imágenes)..."
python manage.py collectstatic --noinput

# NOTA: Reemplaza 'cardsWeb.wsgi:application' si el nombre de la carpeta de tus configuraciones principales es diferente.
echo "🔥 Encendiendo el servidor de producción con Gunicorn..."
exec gunicorn cardsWeb.wsgi:application --bind 0.0.0.0:8001 --workers 3