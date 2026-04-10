# Handoff Greenfield 2026-03-16

Este documento resume el estado actual del proyecto nuevo `LeaseManager` dentro de `Produccion 1.0`.

## 1. Root activo y root legacy

### Root activo nuevo

`D:/Proyectos/LeaseManager/Produccion 1.0`

### Root legacy

`D:/Proyectos/LeaseManager`

Regla:
- el root legacy queda solo como fuente `read-only` para migración, secretos, certificados, schema, integraciones y contraste;
- no borrar, limpiar ni refactorizar el root legacy salvo instrucción explícita del usuario.

## 2. Documentos obligatorios

Leer en este orden:

1. `D:/Proyectos/LeaseManager/Produccion 1.0/AGENTS.md`
2. `D:/Proyectos/LeaseManager/Produccion 1.0/README.md`
3. `D:/Proyectos/LeaseManager/Produccion 1.0/ORDEN_DE_LECTURA.md`
4. `D:/Proyectos/LeaseManager/Produccion 1.0/01_Set_Vigente/PRD_CANONICO.md`
5. `D:/Proyectos/LeaseManager/Produccion 1.0/01_Set_Vigente/MATRIZ_GATES_EXTERNOS.md`
6. `D:/Proyectos/LeaseManager/Produccion 1.0/03_Ejecucion_Tecnica/MODULOS_Y_DEPENDENCIAS.md`
7. `D:/Proyectos/LeaseManager/Produccion 1.0/03_Ejecucion_Tecnica/SECUENCIA_DE_ARRANQUE.md`
8. `D:/Proyectos/LeaseManager/Produccion 1.0/08_Auditoria_Stack/ADR_STACK_FINAL.md`

## 3. Stack obligatorio

Stack canónico del proyecto nuevo:

- `Django 5`
- `Django REST Framework`
- `PostgreSQL`
- `Celery + Redis`
- `React + TypeScript + Vite`

No introducir como base:

- `Next.js`
- `Supabase` como modelo final
- `Django Ninja`
- `pgvector`
- microservicios

## 4. Estructura ya creada

Dentro de `D:/Proyectos/LeaseManager/Produccion 1.0/` ya existen:

- `backend/`
- `frontend/`
- `infra/`
- `migration/`
- `docs/`

## 5. Estado ya implementado

### Backend

En `backend/` ya existe una `PlataformaBase` mínima:

- proyecto Django creado
- `settings.py` por ambiente
- `User` custom
- roles/scopes base
- `AuditEvent`
- `ManualResolution`
- healthchecks
- auth por token
- endpoint de bootstrap de plataforma
- wiring inicial de Celery

Rutas mínimas ya disponibles:

- `/api/v1/auth/login/`
- `/api/v1/auth/logout/`
- `/api/v1/auth/me/`
- `/api/v1/platform/bootstrap/`
- `/api/v1/audit/events/`
- `/api/v1/audit/manual-resolutions/`
- `/api/v1/health/`
- `/api/v1/health/ready/`

### Frontend

En `frontend/` ya existe:

- proyecto React + TypeScript + Vite
- shell inicial de backoffice
- chequeo de health
- login técnico contra la API nueva
- build de producción funcionando

### Infra

En `infra/` ya existe:

- `docker-compose.yml` para PostgreSQL y Redis aislados

### Migración

En `migration/` ya existe:

- contratos explícitos de migración
- script read-only para inventario del root legacy
- inventarios generados

## 6. Inventarios ya generados

En `D:/Proyectos/LeaseManager/Produccion 1.0/migration/inventory/` ya existen:

- `secrets_inventory.json`
- `sensitive_assets_inventory.json`
- `schema_inventory.json`
- `integration_inventory.json`
- `legacy_to_canonical_mapping.json`

## 7. Validaciones ya hechas

Ya se verificó:

- `manage.py check` OK
- `makemigrations` OK
- `migrate` OK usando SQLite temporal para bootstrap local
- smoke test backend:
  - login `200`
  - emisión de token OK
  - health `200`
- `npm run build` del frontend OK

## 8. Limitación abierta

`Docker` está instalado, pero el daemon no estaba corriendo en el momento del bootstrap.

Consecuencia:

- PostgreSQL y Redis reales definidos en `infra/` todavía no se validaron en runtime;
- para no frenar el arranque, se usó un override temporal a SQLite solo para tooling local de Django.

Regla:

- la configuración por defecto del proyecto sigue apuntando a `PostgreSQL + Redis`;
- SQLite no es la base objetivo del proyecto nuevo.

## 9. Reglas críticas de trabajo

- no copiar secretos reales a archivos versionados;
- no mover certificados productivos al repo nuevo;
- no hacer lift-and-shift del schema legacy;
- el modelo final debe seguir el `PRD_CANONICO`, no `types/supabase.ts`;
- si el legacy contradice `Produccion 1.0`, manda `Produccion 1.0`;
- no hacer commit ni deploy todavía;
- no usar `git add .`;
- usar `apply_patch` para ediciones manuales.

## 10. Siguiente paso exacto

Comenzar el módulo `Patrimonio`, siguiendo el orden canónico:

1. `PlataformaBase` ya está bootstrappeada
2. sigue `Patrimonio`
3. luego `Operacion`

En `Patrimonio` debe modelarse como mínimo:

- `Socio`
- `Empresa`
- `ParticipacionPatrimonial`
- `Propiedad`

Y debe mantenerse la separación estricta entre:

- modelo canónico nuevo
- schema legacy read-only

## 11. Qué no rehacer

No volver a:

- scaffold del backend
- scaffold del frontend
- recrear `infra/`
- recrear `migration/`
- reanalizar si `Produccion 1.0` y LeaseManager son el mismo sistema

Eso ya quedó resuelto en esta sesión.

