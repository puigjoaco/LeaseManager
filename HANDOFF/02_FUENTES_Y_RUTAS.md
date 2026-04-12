# Fuentes y Rutas

Nota:

- este inventario enumera los archivos y artefactos relevantes para retomar el trabajo activo al dia de hoy;
- prioriza lo normativo, lo operativo y lo realmente tocado en la etapa de backoffice + RBAC + scope + rollout publico;
- no intenta listar cada archivo del repo.

## 1. Fuentes primarias vigentes

| Ruta absoluta | Tipo | Clasificacion | Tamano | Modificado |
|---|---|---|---:|---|
| [D:/Proyectos/LeaseManager/Produccion 1.0/01_Set_Vigente/PRD_CANONICO.md](/D:/Proyectos/LeaseManager/Produccion%201.0/01_Set_Vigente/PRD_CANONICO.md) | Markdown | fuente primaria | 51213 | 2026-04-10 23:18:05 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/02_ADR_Activos/ADR_ARQUITECTURA_001_BANCA_MULTI_PROVIDER.md](/D:/Proyectos/LeaseManager/Produccion%201.0/02_ADR_Activos/ADR_ARQUITECTURA_001_BANCA_MULTI_PROVIDER.md) | Markdown | fuente primaria | 2387 | 2026-04-10 17:10:37 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/02_ADR_Activos/ADR_ARQUITECTURA_008_CONTABILIDAD_NATIVA.md](/D:/Proyectos/LeaseManager/Produccion%201.0/02_ADR_Activos/ADR_ARQUITECTURA_008_CONTABILIDAD_NATIVA.md) | Markdown | fuente primaria | 5419 | 2026-04-10 17:10:37 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/03_Ejecucion_Tecnica/ROADMAP_TECNICO.md](/D:/Proyectos/LeaseManager/Produccion%201.0/03_Ejecucion_Tecnica/ROADMAP_TECNICO.md) | Markdown | fuente primaria de ejecucion | 4260 | 2026-04-10 17:10:37 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/03_Ejecucion_Tecnica/MODULOS_Y_DEPENDENCIAS.md](/D:/Proyectos/LeaseManager/Produccion%201.0/03_Ejecucion_Tecnica/MODULOS_Y_DEPENDENCIAS.md) | Markdown | fuente primaria de ejecucion | 2718 | 2026-04-10 17:10:37 |
| [D:/Proyectos/LeaseManager/AGENTS.md](/D:/Proyectos/LeaseManager/AGENTS.md) | Markdown | fuente primaria operativa del proyecto general/legacy | 25373 | 2026-03-14 aprox. |

## 2. Contexto operativo del root activo

| Ruta absoluta | Tipo | Clasificacion | Tamano | Modificado |
|---|---|---|---:|---|
| [D:/Proyectos/LeaseManager/Produccion 1.0/README.md](/D:/Proyectos/LeaseManager/Produccion%201.0/README.md) | Markdown | contexto | 3978 | 2026-04-11 22:20:44 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/AGENTS.md](/D:/Proyectos/LeaseManager/Produccion%201.0/AGENTS.md) | Markdown | contexto | 6031 | 2026-04-10 17:10:37 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/infra/docker-compose.yml](/D:/Proyectos/LeaseManager/Produccion%201.0/infra/docker-compose.yml) | YAML | infraestructura local | 821 | 2026-04-10 17:10:37 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/backend/.env](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/.env) | Env | runtime local activo | 548 | 2026-04-10 17:18:48 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/backend/.env.supabase-staging.local](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/.env.supabase-staging.local) | Env | runtime staging local | 237 | 2026-04-10 12:17:22 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/frontend/.vercel/project.json](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/.vercel/project.json) | JSON | enlace local al proyecto Vercel | 128 | 2026-04-12 09:59:00 aprox. |

## 3. Piezas de dominio y migracion que siguen importando

| Ruta absoluta | Tipo | Clasificacion | Tamano | Modificado |
|---|---|---|---:|---|
| [D:/Proyectos/LeaseManager/Produccion 1.0/docs/ESPECIFICACION_TECNICA_FINAL_COMUNIDADES_RECAUDACION_Y_ATRIBUCION.md](/D:/Proyectos/LeaseManager/Produccion%201.0/docs/ESPECIFICACION_TECNICA_FINAL_COMUNIDADES_RECAUDACION_Y_ATRIBUCION.md) | Markdown | borrador vigente del subdominio comunitario | 17714 | 2026-04-06 09:34:53 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/docs/MIGRATION_RUNBOOK.md](/D:/Proyectos/LeaseManager/Produccion%201.0/docs/MIGRATION_RUNBOOK.md) | Markdown | pieza operativa | 3574 | 2026-04-10 19:36:32 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/docs/SUPABASE_STAGING_PLAYBOOK.md](/D:/Proyectos/LeaseManager/Produccion%201.0/docs/SUPABASE_STAGING_PLAYBOOK.md) | Markdown | pieza operativa | 4223 | 2026-04-10 14:00:53 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/migration/enrichments.py](/D:/Proyectos/LeaseManager/Produccion%201.0/migration/enrichments.py) | Python | pieza de trabajo | 8768 | 2026-04-07 00:10:25 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/migration/importers.py](/D:/Proyectos/LeaseManager/Produccion%201.0/migration/importers.py) | Python | pieza de trabajo | 39558 | 2026-04-10 10:48:52 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/migration/orchestration.py](/D:/Proyectos/LeaseManager/Produccion%201.0/migration/orchestration.py) | Python | pieza de trabajo | 3018 | 2026-04-10 23:17:19 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/migration/README.md](/D:/Proyectos/LeaseManager/Produccion%201.0/migration/README.md) | Markdown | contexto operativo de migracion | 4280 | 2026-04-10 19:36:32 |

## 4. Implementacion viva relevante del estado actual

| Ruta absoluta | Tipo | Clasificacion | Tamano | Modificado |
|---|---|---|---:|---|
| [D:/Proyectos/LeaseManager/Produccion 1.0/frontend/src/App.tsx](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/App.tsx) | TypeScript | implementacion viva del backoffice | 119602 | 2026-04-12 11:46:44 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/frontend/src/backoffice/api.ts](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/backoffice/api.ts) | TypeScript | capa de request/base url del backoffice | 1967 | 2026-04-12 11:41:30 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/frontend/src/backoffice/shell.tsx](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/backoffice/shell.tsx) | TypeScript | shell comun del backoffice | 3017 | 2026-04-12 11:15:37 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/frontend/src/backoffice/view-config.ts](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/backoffice/view-config.ts) | TypeScript | config central de tabs y roles | 5288 | 2026-04-12 11:24:58 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/frontend/src/backoffice/shared.tsx](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/backoffice/shared.tsx) | TypeScript | helpers UI extraidos del backoffice | 2879 | 2026-04-12 10:16:39 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/frontend/src/backoffice/workspaces/AuditWorkspace.tsx](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/backoffice/workspaces/AuditWorkspace.tsx) | TypeScript | workspace modularizado de Audit | 6210 | 2026-04-12 00:15:50 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/frontend/src/backoffice/workspaces/DocumentosWorkspace.tsx](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/backoffice/workspaces/DocumentosWorkspace.tsx) | TypeScript | workspace modularizado de Documentos | 16974 | 2026-04-12 00:15:43 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/frontend/src/backoffice/workspaces/CanalesWorkspace.tsx](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/backoffice/workspaces/CanalesWorkspace.tsx) | TypeScript | workspace modularizado de Canales | 10387 | 2026-04-12 00:46:53 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/frontend/src/backoffice/workspaces/ReportingWorkspace.tsx](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/backoffice/workspaces/ReportingWorkspace.tsx) | TypeScript | workspace modularizado de Reporting | 20344 | 2026-04-12 11:43:36 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/frontend/src/backoffice/workspaces/ContabilidadWorkspace.tsx](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/backoffice/workspaces/ContabilidadWorkspace.tsx) | TypeScript | workspace modularizado de Contabilidad | 25064 | 2026-04-12 01:00:52 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/frontend/src/backoffice/workspaces/SiiWorkspace.tsx](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/backoffice/workspaces/SiiWorkspace.tsx) | TypeScript | workspace modularizado de SII | 14496 | 2026-04-12 00:57:09 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/frontend/src/backoffice/workspaces/ComplianceWorkspace.tsx](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/backoffice/workspaces/ComplianceWorkspace.tsx) | TypeScript | workspace modularizado de Compliance | 13213 | 2026-04-12 18:50:46 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/backend/core/permissions.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/permissions.py) | Python | RBAC backend vigente | 3328 | 2026-04-11 23:23:36 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/backend/core/scope_access.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/scope_access.py) | Python | helper central de scope | 6532 | 2026-04-11 16:57:19 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/backend/core/management/commands/seed_demo_access.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/management/commands/seed_demo_access.py) | Python | seed demo reproducible | 16351 | 2026-04-11 16:56:05 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/backend/core/management/commands/bootstrap_demo_operational_data.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/management/commands/bootstrap_demo_operational_data.py) | Python | bootstrap reproducible de UF/pagos/estados de cuenta demo | 7515 | 2026-04-12 18:40:18 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/backend/core/management/commands/bootstrap_demo_control_baseline.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/management/commands/bootstrap_demo_control_baseline.py) | Python | bootstrap reproducible de baseline contable/SII demo | 6954 | 2026-04-12 18:42:23 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/backend/core/management/commands/bootstrap_demo_compliance_exports.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/management/commands/bootstrap_demo_compliance_exports.py) | Python | bootstrap reproducible de exportaciones demo de Compliance | 4077 | 2026-04-12 18:58:53 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/backend/core/management/commands/bootstrap_demo_compliance_policies.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/management/commands/bootstrap_demo_compliance_policies.py) | Python | bootstrap reproducible de políticas demo de retención para Compliance | 2173 | 2026-04-12 19:27:00 aprox. |
| [D:/Proyectos/LeaseManager/Produccion 1.0/backend/core/tests_permissions.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/tests_permissions.py) | Python | evidencia ejecutable de permisos | 5089 | 2026-04-11 23:23:53 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/backend/core/tests_scope_access.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/tests_scope_access.py) | Python | evidencia ejecutable de scope | 14174 | 2026-04-11 23:24:03 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/backend/documentos/scope.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/documentos/scope.py) | Python | filtrado de scope para Documentos | 2300 | 2026-04-11 23:52:41 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/backend/canales/scope.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/canales/scope.py) | Python | filtrado de scope para Canales | 1053 | 2026-04-12 00:05:05 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/backend/compliance/models.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/compliance/models.py) | Python | modelo canónico de retención y exportes sensibles | 2788 | 2026-03-22 06:47:37 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/backend/compliance/serializers.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/compliance/serializers.py) | Python | serializers de Compliance | 3605 | 2026-03-22 06:48:11 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/backend/compliance/services.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/compliance/services.py) | Python | servicios de cifrado/exportación sensible | 2965 | 2026-03-22 06:47:37 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/backend/compliance/views.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/compliance/views.py) | Python | endpoints admin-only de Compliance | 6069 | 2026-04-11 15:57:17 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/backend/compliance/urls.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/compliance/urls.py) | Python | rutas de Compliance | 1055 | 2026-03-22 06:48:11 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/backend/leasemanager_api/settings.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/leasemanager_api/settings.py) | Python | settings con normalización de clave de exportación sensible | 6045 | 2026-04-12 18:53:33 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/backend/health/views.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/health/views.py) | Python | health y ready checks del backend publico | 1680 | 2026-04-10 17:11:23 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/backend/health/urls.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/health/urls.py) | Python | rutas de health y ready | 135 | 2026-04-10 17:11:23 aprox. |

## 5. Artefactos de deploy y rollout publico

| Ruta absoluta | Tipo | Clasificacion | Tamano | Modificado |
|---|---|---|---:|---|
| [D:/Proyectos/LeaseManager/Produccion 1.0/docs/DEPLOY_FRONTEND_VERCEL.md](/D:/Proyectos/LeaseManager/Produccion%201.0/docs/DEPLOY_FRONTEND_VERCEL.md) | Markdown | decision/operacion de deploy frontend | 1887 | 2026-04-12 10:01:18 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/docs/DEPLOY_BACKEND_GREENFIELD.md](/D:/Proyectos/LeaseManager/Produccion%201.0/docs/DEPLOY_BACKEND_GREENFIELD.md) | Markdown | decision/operacion de deploy backend | 5024 | 2026-04-12 13:02:03 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/docs/ROLL_OUT_BACKEND_FRONTEND.md](/D:/Proyectos/LeaseManager/Produccion%201.0/docs/ROLL_OUT_BACKEND_FRONTEND.md) | Markdown | checklist de conexion frontend/backend | 3452 | 2026-04-12 13:09:17 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/backend/railway.web.json](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/railway.web.json) | JSON | config as code del web service Railway | 276 | 2026-04-12 13:01:50 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/backend/railway.worker.json](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/railway.worker.json) | JSON | config as code del worker Railway | 301 | 2026-04-12 12:19:24 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/scripts/connect-frontend-to-backend.ps1](/D:/Proyectos/LeaseManager/Produccion%201.0/scripts/connect-frontend-to-backend.ps1) | PowerShell | helper de upsert/redeploy Vercel | 1954 | 2026-04-12 13:09:17 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/push-and-deploy.bat](/D:/Proyectos/LeaseManager/Produccion%201.0/push-and-deploy.bat) | Batch | flujo local de push + deploy frontend | 2963 | 2026-03-15 07:52:00 aprox. |

## 6. Artefactos validados y evidencia de migracion

| Ruta absoluta | Tipo | Clasificacion | Tamano | Modificado |
|---|---|---|---:|---|
| [D:/Proyectos/LeaseManager/Produccion 1.0/migration/bundles/supabase_staging_verification_2026-04-10.json](/D:/Proyectos/LeaseManager/Produccion%201.0/migration/bundles/supabase_staging_verification_2026-04-10.json) | JSON | evidencia validada | 1386 | 2026-04-10 12:32:02 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/migration/bundles/verify_current_migration_target_supabase.json](/D:/Proyectos/LeaseManager/Produccion%201.0/migration/bundles/verify_current_migration_target_supabase.json) | JSON | evidencia validada | 1818 | 2026-04-10 23:17:37 |
| [D:/Proyectos/LeaseManager/Produccion 1.0/backend/bundle-inspect-final.db](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/bundle-inspect-final.db) | SQLite | evidencia historica de inspeccion | 1384448 | 2026-04-07 00:15:03 |

## 7. Contexto git y runtime publico

Contexto operativo no basado en un archivo:

- git root activo: `D:/Proyectos/LeaseManager/Produccion 1.0`
- `HEAD` funcional previo a este refresh: `6877014`
- commits de rollout conectado:
  - `3850612` `chore: trigger connected deployment rebuilds`
  - `9068f7e` `chore: trigger vercel build with frontend root`
  - `f83dafb` `feat: add compliance workspace to backoffice`
  - `5aa2fca` `fix: normalize compliance export encryption keys`
  - `6877014` `feat: add demo compliance export bootstrap command`
- proyecto Vercel activo: `leasemanager-backoffice`
- alias productivo actual del frontend:
  - `https://leasemanager-backoffice.vercel.app`
- proyecto Railway activo: `content-friendship`
- web service Railway:
  - `surprising-balance`
- worker Railway:
  - `spirited-recreation`
- backend publico actual:
  - `https://surprising-balance-production.up.railway.app`
- health publico validado:
  - `/api/v1/health/`
  - `/api/v1/health/ready/`

## 8. Respuestas externas y material no versionado

### Respuestas externas

- las respuestas externas literales siguen archivadas en [07_RESPUESTAS_EXTERNAS_LITERAL.md](/D:/Proyectos/LeaseManager/Produccion%201.0/HANDOFF/07_RESPUESTAS_EXTERNAS_LITERAL.md)

### Material no versionado importante para continuidad

- datos `TEST LOCAL` en la base local `v7`;
- usuario local `admin` de desarrollo;
- usuarios demo reproducibles (`demo-admin`, `demo-operador`, `demo-revisor`, `demo-socio`) sembrados localmente;
- usuarios demo sembrados tambien en la base remota publica;
- estado vivo de Docker/PostgreSQL/Redis/backend/frontend locales;
- sesiones locales activas de browser/Vercel/Railway durante esta fase;
- configuracion local fuera del repo que volvio a dejar operativo el MCP de Playwright.
