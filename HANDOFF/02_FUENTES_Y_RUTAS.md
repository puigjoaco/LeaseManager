# Fuentes y Rutas

Nota:

- este inventario enumera los archivos y artefactos relevantes para retomar el trabajo activo al día de hoy;
- prioriza lo normativo, lo operativo y lo realmente tocado en la etapa de backoffice + RBAC + scope;
- no intenta listar cada archivo del repo.

## 1. Fuentes primarias vigentes

| Ruta absoluta | Tipo | Clasificación |
|---|---|---|
| [D:/Proyectos/LeaseManager/Produccion 1.0/01_Set_Vigente/PRD_CANONICO.md](/D:/Proyectos/LeaseManager/Produccion%201.0/01_Set_Vigente/PRD_CANONICO.md) | Markdown | fuente primaria |
| [D:/Proyectos/LeaseManager/Produccion 1.0/02_ADR_Activos/ADR_ARQUITECTURA_001_BANCA_MULTI_PROVIDER.md](/D:/Proyectos/LeaseManager/Produccion%201.0/02_ADR_Activos/ADR_ARQUITECTURA_001_BANCA_MULTI_PROVIDER.md) | Markdown | fuente primaria |
| [D:/Proyectos/LeaseManager/Produccion 1.0/02_ADR_Activos/ADR_ARQUITECTURA_008_CONTABILIDAD_NATIVA.md](/D:/Proyectos/LeaseManager/Produccion%201.0/02_ADR_Activos/ADR_ARQUITECTURA_008_CONTABILIDAD_NATIVA.md) | Markdown | fuente primaria |
| [D:/Proyectos/LeaseManager/Produccion 1.0/03_Ejecucion_Tecnica/ROADMAP_TECNICO.md](/D:/Proyectos/LeaseManager/Produccion%201.0/03_Ejecucion_Tecnica/ROADMAP_TECNICO.md) | Markdown | fuente primaria de ejecución |
| [D:/Proyectos/LeaseManager/Produccion 1.0/03_Ejecucion_Tecnica/MODULOS_Y_DEPENDENCIAS.md](/D:/Proyectos/LeaseManager/Produccion%201.0/03_Ejecucion_Tecnica/MODULOS_Y_DEPENDENCIAS.md) | Markdown | fuente primaria de ejecución |
| [D:/Proyectos/LeaseManager/AGENTS.md](/D:/Proyectos/LeaseManager/AGENTS.md) | Markdown | fuente primaria operativa del proyecto general/legacy |

## 2. Contexto operativo del root activo

| Ruta absoluta | Tipo | Clasificación |
|---|---|---|
| [D:/Proyectos/LeaseManager/Produccion 1.0/README.md](/D:/Proyectos/LeaseManager/Produccion%201.0/README.md) | Markdown | contexto |
| [D:/Proyectos/LeaseManager/Produccion 1.0/AGENTS.md](/D:/Proyectos/LeaseManager/Produccion%201.0/AGENTS.md) | Markdown | contexto |
| [D:/Proyectos/LeaseManager/Produccion 1.0/infra/docker-compose.yml](/D:/Proyectos/LeaseManager/Produccion%201.0/infra/docker-compose.yml) | YAML | infraestructura local |
| [D:/Proyectos/LeaseManager/Produccion 1.0/backend/.env](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/.env) | Env | runtime local activo |
| [D:/Proyectos/LeaseManager/Produccion 1.0/backend/.env.supabase-staging.local](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/.env.supabase-staging.local) | Env | runtime staging local |

## 3. Piezas de dominio y migración que siguen importando

| Ruta absoluta | Tipo | Clasificación |
|---|---|---|
| [D:/Proyectos/LeaseManager/Produccion 1.0/docs/ESPECIFICACION_TECNICA_FINAL_COMUNIDADES_RECAUDACION_Y_ATRIBUCION.md](/D:/Proyectos/LeaseManager/Produccion%201.0/docs/ESPECIFICACION_TECNICA_FINAL_COMUNIDADES_RECAUDACION_Y_ATRIBUCION.md) | Markdown | borrador vigente del subdominio comunitario |
| [D:/Proyectos/LeaseManager/Produccion 1.0/docs/MIGRATION_RUNBOOK.md](/D:/Proyectos/LeaseManager/Produccion%201.0/docs/MIGRATION_RUNBOOK.md) | Markdown | pieza operativa |
| [D:/Proyectos/LeaseManager/Produccion 1.0/docs/SUPABASE_STAGING_PLAYBOOK.md](/D:/Proyectos/LeaseManager/Produccion%201.0/docs/SUPABASE_STAGING_PLAYBOOK.md) | Markdown | pieza operativa |
| [D:/Proyectos/LeaseManager/Produccion 1.0/migration/enrichments.py](/D:/Proyectos/LeaseManager/Produccion%201.0/migration/enrichments.py) | Python | pieza de trabajo |
| [D:/Proyectos/LeaseManager/Produccion 1.0/migration/importers.py](/D:/Proyectos/LeaseManager/Produccion%201.0/migration/importers.py) | Python | pieza de trabajo |
| [D:/Proyectos/LeaseManager/Produccion 1.0/migration/orchestration.py](/D:/Proyectos/LeaseManager/Produccion%201.0/migration/orchestration.py) | Python | pieza de trabajo |

## 4. Implementación viva relevante del estado actual

| Ruta absoluta | Tipo | Clasificación |
|---|---|---|
| [D:/Proyectos/LeaseManager/Produccion 1.0/frontend/src/App.tsx](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/App.tsx) | TypeScript | implementación viva del backoffice |
| [D:/Proyectos/LeaseManager/Produccion 1.0/frontend/src/App.css](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/App.css) | CSS | implementación viva del backoffice |
| [D:/Proyectos/LeaseManager/Produccion 1.0/backend/core/permissions.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/permissions.py) | Python | implementación viva de RBAC backend |
| [D:/Proyectos/LeaseManager/Produccion 1.0/backend/core/scope_access.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/scope_access.py) | Python | helper central de scope |
| [D:/Proyectos/LeaseManager/Produccion 1.0/backend/core/management/commands/seed_demo_access.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/management/commands/seed_demo_access.py) | Python | seed demo reproducible |
| [D:/Proyectos/LeaseManager/Produccion 1.0/backend/core/tests_permissions.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/tests_permissions.py) | Python | evidencia ejecutable de RBAC |
| [D:/Proyectos/LeaseManager/Produccion 1.0/backend/core/tests_scope_access.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/tests_scope_access.py) | Python | evidencia ejecutable de scope |
| [D:/Proyectos/LeaseManager/Produccion 1.0/backend/reporting/services.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/reporting/services.py) | Python | reporting ya endurecido por scope |
| [D:/Proyectos/LeaseManager/Produccion 1.0/backend/patrimonio/views.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/patrimonio/views.py) | Python | implementación actual |
| [D:/Proyectos/LeaseManager/Produccion 1.0/backend/operacion/views.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/operacion/views.py) | Python | implementación actual |
| [D:/Proyectos/LeaseManager/Produccion 1.0/backend/contratos/views.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/contratos/views.py) | Python | implementación actual |
| [D:/Proyectos/LeaseManager/Produccion 1.0/backend/cobranza/views.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/cobranza/views.py) | Python | implementación actual |
| [D:/Proyectos/LeaseManager/Produccion 1.0/backend/conciliacion/views.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/conciliacion/views.py) | Python | implementación actual |
| [D:/Proyectos/LeaseManager/Produccion 1.0/backend/contabilidad/views.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/contabilidad/views.py) | Python | implementación actual |
| [D:/Proyectos/LeaseManager/Produccion 1.0/backend/sii/views.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/sii/views.py) | Python | implementación actual |

## 5. Artefactos validados y evidencia de migración

| Ruta absoluta | Tipo | Clasificación |
|---|---|---|
| [D:/Proyectos/LeaseManager/Produccion 1.0/migration/bundles/supabase_staging_verification_2026-04-10.json](/D:/Proyectos/LeaseManager/Produccion%201.0/migration/bundles/supabase_staging_verification_2026-04-10.json) | JSON | evidencia validada |
| [D:/Proyectos/LeaseManager/Produccion 1.0/migration/bundles/verify_current_migration_target_supabase.json](/D:/Proyectos/LeaseManager/Produccion%201.0/migration/bundles/verify_current_migration_target_supabase.json) | JSON | evidencia validada |
| [D:/Proyectos/LeaseManager/Produccion 1.0/backend/bundle-inspect-final.db](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/bundle-inspect-final.db) | SQLite | evidencia histórica de inspección |

## 6. Contexto git y remotos

Contexto operativo no basado en un archivo:

- git root activo: `D:/Proyectos/LeaseManager/Produccion 1.0`
- `HEAD` actual: `bdde843`
- commits relevantes recientes:
  - `550becf` `feat: seed demo access profiles for rbac validation`
  - `811b8ff` `fix: enforce scoped backend visibility for non-admin roles`
  - `bdde843` `fix: scope write paths for non-admin backoffice actions`
- working tree actual: `dirty` por refresh local de `HANDOFF/*` y docs.

## 7. Respuestas externas y material no versionado

### Respuestas externas

- las respuestas externas literales siguen archivadas en [07_RESPUESTAS_EXTERNAS_LITERAL.md](/D:/Proyectos/LeaseManager/Produccion%201.0/HANDOFF/07_RESPUESTAS_EXTERNAS_LITERAL.md)

### Material no versionado importante para continuidad

- datos `TEST LOCAL` en la base local `v7`;
- usuario local `admin` de desarrollo;
- usuarios demo `demo-admin`, `demo-operador`, `demo-revisor`, `demo-socio`;
- estado vivo de Docker/PostgreSQL/Redis/backend/frontend.
