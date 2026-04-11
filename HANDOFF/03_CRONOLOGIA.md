# Cronologia

## Linea secuencial y lineal del trabajo relevante

| Fecha | Hito | Documento o soporte | Relevancia |
|---|---|---|---|
| 2026-03-15 | Se consolida el set activo del greenfield | [PRD_CANONICO.md](/D:/Proyectos/LeaseManager/Produccion%201.0/01_Set_Vigente/PRD_CANONICO.md), ADRs activos | Base canónica de producto, dominio y stack |
| 2026-03-22 a 2026-03-24 | Se endurece el pipeline legacy -> canonical | [importers.py](/D:/Proyectos/LeaseManager/Produccion%201.0/migration/importers.py), [transformers.py](/D:/Proyectos/LeaseManager/Produccion%201.0/migration/transformers.py) | Idempotencia, `ManualResolution`, resecuenciación de períodos |
| 2026-04-05 a 2026-04-06 | Se cierra el diseño comunitario y se implementa en backend | [ESPECIFICACION_TECNICA_FINAL_COMUNIDADES_RECAUDACION_Y_ATRIBUCION.md](/D:/Proyectos/LeaseManager/Produccion%201.0/docs/ESPECIFICACION_TECNICA_FINAL_COMUNIDADES_RECAUDACION_Y_ATRIBUCION.md), `backend/*` | El problema comunitario pasa de análisis a implementación |
| 2026-04-08 a 2026-04-10 | Validación local PostgreSQL, staging Supabase, rename a `LeaseManager` y separación de repo | artefactos `v7`, `v9`, Supabase staging, commits `cadde62`, `c6add42` | Queda cerrado el tramo de migración + naming + repo |
| 2026-04-10 | Commit `5732c78` | `feat: add patrimonio operations workspace and sanitize migration metadata` | Se corrige la exposición de metadata sensible y se abre la primera superficie real del backoffice |
| 2026-04-11 | Commit `310bc03` | `feat: add patrimonio and operations creation forms` | El backoffice pasa de lectura a operación básica en `Patrimonio` y `Operacion` |
| 2026-04-11 | Se levanta Docker Desktop y la infra local | [docker-compose.yml](/D:/Proyectos/LeaseManager/Produccion%201.0/infra/docker-compose.yml) | `postgres` y `redis` locales quedan operativos |
| 2026-04-11 | Se reconstruye localmente `leasemanager_migration_run_20260409_v7` | [rehearse_current_migration_flow.py](/D:/Proyectos/LeaseManager/Produccion%201.0/migration/scripts/rehearse_current_migration_flow.py) | El baseline local queda otra vez usable sobre PostgreSQL |
| 2026-04-11 | Se crea usuario local admin y fixtures `TEST LOCAL` | operación local sobre DB | Se habilita validación manual/end-to-end del backoffice en entorno local |
| 2026-04-11 | Commits `8bd1eb0`, `302d4d9`, `ce395bb`, `a167a39`, `cb579f1`, `c4b4af9`, `ff89b30` | backoffice por módulos | Se abren `Contratos`, `Cobranza`, `Conciliacion`, `Contabilidad`, `SII` y `Reporting` en frontend |
| 2026-04-11 | Commits `c217219`, `fbe4da1`, `d9b4889`, `9bd8912`, `df44f1b` | acciones rápidas, navegación, edición, UI por rol, RBAC API | La app deja de ser solo UI bonita y pasa a respetar backend real |
| 2026-04-11 | Commit `550becf` | `feat: seed demo access profiles for rbac validation` | Se crea el seed reproducible de usuarios/roles/scopes demo |
| 2026-04-11 | Commit `811b8ff` | `fix: enforce scoped backend visibility for non-admin roles` | Se agrega filtrado inicial de lectura por scope en backend |
| 2026-04-11 | Commit `bdde843` | `fix: scope write paths for non-admin backoffice actions` | Se endurecen writes y acciones con IDs directos para perfiles no-admin |
| 2026-04-11 | Se corre la suite ampliada de scope/RBAC | [tests_scope_access.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/tests_scope_access.py), `operacion.tests`, `contratos.tests`, `cobranza.tests`, `conciliacion.tests`, `reporting.tests`, `sii.tests`, `contabilidad.tests` | Se valida lectura y escritura scopeada sobre el backend vivo |
| 2026-04-11 | Se actualiza el paquete `HANDOFF/` local | working tree local | La continuidad queda alineada con seed demo + hardening de scope |
