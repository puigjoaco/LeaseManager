# Greenfield Bootstrap

## Objetivo

Levantar la plataforma nueva de LeaseManager dentro de `Produccion 1.0` sin tocar el root legacy.

## Pasos base

1. Levantar `infra/docker-compose.yml`
2. Configurar `backend/.env`
3. Ejecutar migraciones Django
4. Crear superusuario
5. Instalar y levantar `frontend/`
6. Ejecutar inventario read-only del root actual

## Entregables ya preparados

- backend Django/DRF con auth, audit y healthchecks
- frontend React/Vite con shell inicial
- infra local con PostgreSQL y Redis
- capa de migración con inventarios sanitizados

