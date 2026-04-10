# LeaseManager Backend

Backend greenfield basado en `Django 5 + DRF + Celery + PostgreSQL + Redis`.

## Arranque local

1. Crear `.env` desde `.env.example`
2. Levantar `infra/docker-compose.yml`
3. Activar `.venv`
4. Ejecutar migraciones
5. Crear superusuario

## Apps base

- `users`: usuario, login, token y perfil actual
- `core`: roles, scopes y configuracion base
- `audit`: `EventoAuditable` y `ResolucionManual`
- `health`: healthchecks de app, DB y Redis

