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

- dependencias de runtime agregadas en [requirements.txt](/D:/Proyectos/LeaseManager/backend/requirements.txt):
  - `gunicorn`
  - `whitenoise`
- middleware y storage de estáticos preparados en [settings.py](/D:/Proyectos/LeaseManager/backend/leasemanager_api/settings.py)
- comando de arranque web listo en [Procfile](/D:/Proyectos/LeaseManager/backend/Procfile)

## Variables mínimas

Usar [backend/.env.example](/D:/Proyectos/LeaseManager/backend/.env.example) como base y completar al menos:

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG=false`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CORS_ALLOWED_ORIGINS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`
- `DJANGO_SECURE_SSL_REDIRECT`
- `DJANGO_SECURE_HSTS_SECONDS`
- `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS`
- `DJANGO_SECURE_HSTS_PRELOAD`
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

## Ruta Docker

Artefactos ya preparados:

- [backend/Dockerfile](/D:/Proyectos/LeaseManager/backend/Dockerfile)
- [backend/.dockerignore](/D:/Proyectos/LeaseManager/backend/.dockerignore)
- [backend/docker-entrypoint.sh](/D:/Proyectos/LeaseManager/backend/docker-entrypoint.sh)

Build:

```bash
docker build -t leasemanager-backend ./backend
```

Run:

```bash
docker run --rm -p 8000:8000 \
  -e DJANGO_SECRET_KEY=replace-me \
  -e DJANGO_DEBUG=false \
  -e DJANGO_ALLOWED_HOSTS=your-host \
  -e DJANGO_CORS_ALLOWED_ORIGINS=https://your-frontend \
  -e DJANGO_CSRF_TRUSTED_ORIGINS=https://your-frontend \
  -e DATABASE_URL=postgresql://... \
  -e REDIS_URL=redis://... \
  -e CELERY_RESULT_BACKEND=redis://... \
  -e FRONTEND_URL=https://your-frontend \
  -e LEGACY_ROOT_PATH=/app \
  leasemanager-backend
```

## Ruta Railway recomendada

Topología sugerida dentro de un mismo proyecto Railway:

1. servicio `backend-web`
2. servicio `backend-worker`
3. PostgreSQL
4. Redis

Config as code preparada:

- [backend/railway.web.json](/D:/Proyectos/LeaseManager/backend/railway.web.json)
- [backend/railway.worker.json](/D:/Proyectos/LeaseManager/backend/railway.worker.json)
- [backend/railway.env.example](/D:/Proyectos/LeaseManager/backend/railway.env.example)
- [scripts/railway-backend-bootstrap.ps1](/D:/Proyectos/LeaseManager/scripts/railway-backend-bootstrap.ps1)

### Servicio web

- root directory: `/backend`
- config path: `/backend/railway.web.json`
- usa el `Dockerfile` del backend
- healthcheck real: `/api/v1/health/ready/`

### Servicio worker

- root directory: `/backend`
- config path: `/backend/railway.worker.json`
- usa la misma imagen, pero sobreescribe `startCommand` para Celery worker

### Variables adicionales útiles

- `DJANGO_DEBUG=false`
- `DJANGO_SECURE_SSL_REDIRECT=true`
- `DJANGO_SECURE_HSTS_SECONDS=31536000`
- `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=true`
- `DJANGO_SECURE_HSTS_PRELOAD=false`
- `CELERY_LOGLEVEL=info`
- `PORT` gestionado por Railway

### Nota

La validación de estas configuraciones queda pendiente de crear el proyecto Railway real del backend, pero la estructura ya está lista para usarse sin improvisación.

Bootstrap asistido seguro:

Primero ejecutar preflight local. Este comando valida el archivo de variables
de ejemplo y muestra el plan sin llamar a Railway ni crear recursos:

```powershell
.\scripts\railway-backend-bootstrap.ps1
```

Para aplicar cambios reales en Railway se requiere opt-in explicito:

```powershell
.\scripts\railway-backend-bootstrap.ps1 `
  -Environment staging `
  -CreateRedis `
  -AuthorizationRef "railway-bootstrap-autorizado-YYYYMMDD" `
  -Apply
```

El script usa por defecto [backend/railway.env.example](/D:/Proyectos/LeaseManager/backend/railway.env.example),
no rutas legacy. No imprime valores de variables; en comandos `variable set`
solo muestra claves con valor redactado. Si se usa un archivo de variables real,
ese archivo debe entregarse fuera del repo y con autorización concreta.

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
- si la plataforma usa proxy HTTPS, [settings.py](/D:/Proyectos/LeaseManager/backend/leasemanager_api/settings.py) ya quedó preparado con `SECURE_PROXY_SSL_HEADER`;
- cuando `DJANGO_DEBUG=false`, el backend ya aplica cookies seguras, `X_FRAME_OPTIONS=DENY`, `SECURE_CONTENT_TYPE_NOSNIFF` y HSTS configurable.
