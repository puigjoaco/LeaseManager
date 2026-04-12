# Deploy Backend Greenfield

Estado: preparado para siguiente etapa de publicación

## Objetivo

Dejar el backend Django del greenfield listo para desplegar en una plataforma tipo service/container sin volver a improvisar la parte básica de producción.

## Base técnica

- framework: `Django 5`
- servidor recomendado: `gunicorn`
- estáticos servidos por app: `whitenoise`
- base de datos: `PostgreSQL`
- broker/result backend: `Redis`

## Cambios ya preparados

- dependencias de runtime agregadas en [requirements.txt](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/requirements.txt):
  - `gunicorn`
  - `whitenoise`
- middleware y storage de estáticos preparados en [settings.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/leasemanager_api/settings.py)
- comando de arranque web listo en [Procfile](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/Procfile)

## Variables mínimas

Usar [backend/.env.example](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/.env.example) como base y completar al menos:

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG=false`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CORS_ALLOWED_ORIGINS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`
- `DATABASE_URL`
- `REDIS_URL`
- `CELERY_RESULT_BACKEND`
- `FRONTEND_URL`

## Comandos mínimos

### Instalación

```bash
pip install -r requirements.txt
```

### Validación

```bash
python manage.py check
python manage.py migrate
python manage.py collectstatic --noinput
```

### Arranque web

```bash
gunicorn leasemanager_api.wsgi:application --bind 0.0.0.0:$PORT --log-file -
```

## Nota de validación local

- `collectstatic --noinput` ya quedó validado localmente;
- `gunicorn` no se valida en Windows porque depende de `fcntl`;
- la validación real de `gunicorn` debe hacerse en un runtime Linux, que es el entorno esperado para producción;
- para desarrollo local en Windows se sigue usando:

```bash
python manage.py runserver 127.0.0.1:8000
```

## Notas importantes

- este documento no fija todavía una plataforma final de hosting;
- la URL pública final del backend sigue siendo un dato externo pendiente;
- cuando esa URL exista, debe conectarse con el frontend vía `VITE_API_BASE_URL`;
- si la plataforma usa proxy HTTPS, [settings.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/leasemanager_api/settings.py) ya quedó preparado con `SECURE_PROXY_SSL_HEADER`.
