# Rollout Backend + Frontend

Estado: checklist operativo para cerrar la publicación del greenfield

## Objetivo

Conectar la topología ya definida:

- frontend en Vercel
- backend web + worker en Railway
- PostgreSQL gestionado
- Redis gestionado

y terminar el enlace del frontend con `VITE_API_BASE_URL`.

## Orden recomendado

1. crear proyecto Railway del backend
2. crear servicio `backend-web`
3. crear servicio `backend-worker`
4. crear PostgreSQL
5. crear Redis
6. configurar variables del backend
7. desplegar `backend-web`
8. desplegar `backend-worker`
9. tomar URL pública del backend
10. configurar `VITE_API_BASE_URL` en Vercel
11. validar punta a punta

## Backend web en Railway

### Código fuente

- root directory: `backend`
- imagen: [backend/Dockerfile](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/Dockerfile)
- config: [backend/railway.web.json](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/railway.web.json)

### Variables mínimas

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG=false`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CORS_ALLOWED_ORIGINS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`
- `DATABASE_URL`
- `REDIS_URL`
- `CELERY_RESULT_BACKEND`
- `FRONTEND_URL`
- `LEGACY_ROOT_PATH=/app`

### Healthcheck esperado

- `/api/v1/health/`

## Backend worker en Railway

### Código fuente

- root directory: `backend`
- imagen: misma del backend web
- config: [backend/railway.worker.json](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/railway.worker.json)

### Variables mínimas

Las mismas del backend web, más:

- `CELERY_LOGLEVEL=info`

## PostgreSQL

Puedes usar:

- PostgreSQL en Railway
- o Supabase Postgres si quieres mantener la base ahí

Recomendación actual:

- si ya existe staging útil en Supabase y quieres minimizar migraciones, mantener Postgres en Supabase;
- si quieres simplificar red privada y operación en un solo lugar, usar PostgreSQL de Railway.

## Redis

Recomendación actual:

- Railway Redis

Motivo:

- simplifica conexión del backend web y worker;
- evita dejar Redis “pendiente” cuando ya está en settings y healthchecks.

## Frontend en Vercel

Proyecto actual:

- [https://leasemanager-backoffice.vercel.app](https://leasemanager-backoffice.vercel.app)

Variable pendiente de producción:

- `VITE_API_BASE_URL`

Valor esperado:

- la URL pública HTTPS del `backend-web`

Automatización preparada:

- [scripts/connect-frontend-to-backend.ps1](/D:/Proyectos/LeaseManager/Produccion%201.0/scripts/connect-frontend-to-backend.ps1)

Ejemplo:

```powershell
.\scripts\connect-frontend-to-backend.ps1 -BackendUrl "https://backend-web-production.up.railway.app"
```

Ese script:

1. hace upsert de `VITE_API_BASE_URL` en Vercel;
2. actualiza `production` y `preview`;
3. dispara redeploy del frontend.

## Checklist de cierre

- `backend-web` responde `200` en `/api/v1/health/`
- login del frontend deja de estar deshabilitado en producción
- `demo-admin` inicia sesión desde Vercel
- tabs visibles por rol siguen correctos
- `demo-revisor` y `demo-socio` mantienen banners readonly
- no aparecen errores de CORS
- no aparecen errores `401` por base URL incorrecta

## Criterio para considerar esta etapa cerrada

La etapa queda cerrada cuando:

1. existe URL pública del backend;
2. `VITE_API_BASE_URL` apunta a esa URL;
3. el frontend público deja de mostrar el mensaje de backend faltante;
4. al menos `demo-admin` y `demo-operador` navegan end to end desde el frontend público.
