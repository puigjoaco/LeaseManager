# Greenfield Bootstrap

## Objetivo

Levantar la plataforma nueva de LeaseManager dentro del root limpio activo
`D:/Proyectos/LeaseManager`, sin tocar los savegames historicos.

## Pasos base

1. Levantar `infra/docker-compose.yml`
2. Configurar `backend/.env`
3. Ejecutar migraciones Django
4. Crear superusuario
5. Instalar y levantar `frontend/`
6. Ejecutar inventario read-only del root historico/savegame cuando el alcance
   requiera rescate de informacion

## Entregables ya preparados

- backend Django/DRF con auth, audit y healthchecks
- frontend React/Vite con shell inicial
- infra local con PostgreSQL y Redis
- capa de migración con inventarios sanitizados

