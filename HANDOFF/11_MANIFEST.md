# Manifest

Ultima actualizacion del manifest: 2026-04-12

Nota metodologica:

- este inventario lista los archivos clave efectivamente usados para retomar el trabajo actual;
- cuando un archivo sensible fue abierto solo para confirmar contexto operativo, se marca como `inspeccion parcial`;
- la referencia Git se expresa contra el ultimo tramo funcional previo a este refresh documental, para no confundir el cierre del producto con la actualizacion del paquete.

## 1. Fuentes primarias y operativas clave

| Ruta absoluta | Tamano | Modificado | Rol dentro del proyecto | Estado de lectura |
|---|---:|---|---|---|
| `D:\Proyectos\LeaseManager\Produccion 1.0\README.md` | 3978 | 2026-04-11 22:20:44 | contexto general del root activo | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\AGENTS.md` | 6031 | 2026-04-10 17:10:37 | instrucciones operativas del greenfield activo | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\01_Set_Vigente\PRD_CANONICO.md` | 51213 | 2026-04-10 23:18:05 | fuente primaria canonica del producto | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\02_ADR_Activos\ADR_ARQUITECTURA_001_BANCA_MULTI_PROVIDER.md` | 2387 | 2026-04-10 17:10:37 | decision arquitectonica activa de banca | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\02_ADR_Activos\ADR_ARQUITECTURA_008_CONTABILIDAD_NATIVA.md` | 5419 | 2026-04-10 17:10:37 | decision arquitectonica activa de contabilidad | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\03_Ejecucion_Tecnica\ROADMAP_TECNICO.md` | 4260 | 2026-04-10 17:10:37 | roadmap tecnico vigente | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\03_Ejecucion_Tecnica\MODULOS_Y_DEPENDENCIAS.md` | 2718 | 2026-04-10 17:10:37 | mapa de modulos y dependencias | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\docs\ESPECIFICACION_TECNICA_FINAL_COMUNIDADES_RECAUDACION_Y_ATRIBUCION.md` | 17714 | 2026-04-06 09:34:53 | base tecnica del subdominio comunitario ya cerrado | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\docs\MIGRATION_RUNBOOK.md` | 3574 | 2026-04-10 19:36:32 | runbook operativo de migracion local | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\docs\SUPABASE_STAGING_PLAYBOOK.md` | 4223 | 2026-04-10 14:00:53 | playbook de staging Supabase | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\infra\docker-compose.yml` | 821 | 2026-04-10 17:10:37 | infraestructura local de PostgreSQL y Redis | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\backend\.env` | 548 | 2026-04-10 17:18:48 | runtime local activo del backend | inspeccion parcial |
| `D:\Proyectos\LeaseManager\Produccion 1.0\backend\.env.supabase-staging.local` | 237 | 2026-04-10 12:17:22 | runtime staging local para Supabase | inspeccion parcial |

## 2. Implementacion viva y evidencia ejecutable

| Ruta absoluta | Tamano | Modificado | Rol dentro del proyecto | Estado de lectura |
|---|---:|---|---|---|
| `D:\Proyectos\LeaseManager\Produccion 1.0\frontend\src\App.tsx` | 119602 | 2026-04-12 11:46:44 | implementacion viva del backoffice multiworkspace | leido por tramos |
| `D:\Proyectos\LeaseManager\Produccion 1.0\frontend\src\backoffice\api.ts` | 1967 | 2026-04-12 11:41:30 | capa de request/base url del backoffice | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\frontend\src\backoffice\shell.tsx` | 3017 | 2026-04-12 11:15:37 | shell comun del backoffice | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\frontend\src\backoffice\view-config.ts` | 5288 | 2026-04-12 11:24:58 | config central de tabs y roles | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\frontend\src\backoffice\workspaces\AuditWorkspace.tsx` | 6210 | 2026-04-12 00:15:50 | workspace modularizado de Audit | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\frontend\src\backoffice\workspaces\DocumentosWorkspace.tsx` | 16974 | 2026-04-12 00:15:43 | workspace modularizado de Documentos | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\frontend\src\backoffice\workspaces\CanalesWorkspace.tsx` | 10387 | 2026-04-12 00:46:53 | workspace modularizado de Canales | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\frontend\src\backoffice\workspaces\ReportingWorkspace.tsx` | 20344 | 2026-04-12 11:43:36 | workspace modularizado de Reporting | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\frontend\src\backoffice\workspaces\ContabilidadWorkspace.tsx` | 25064 | 2026-04-12 01:00:52 | workspace modularizado de Contabilidad | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\frontend\src\backoffice\workspaces\SiiWorkspace.tsx` | 14496 | 2026-04-12 00:57:09 | workspace modularizado de SII | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\backend\core\permissions.py` | 3328 | 2026-04-11 23:23:36 | politica RBAC backend vigente | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\backend\core\scope_access.py` | 6532 | 2026-04-11 16:57:19 | helper central de filtrado por scope | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\backend\core\management\commands\seed_demo_access.py` | 16351 | 2026-04-11 16:56:05 | seed reproducible de usuarios/roles/scopes demo | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\backend\core\tests_permissions.py` | 5089 | 2026-04-11 23:23:53 | evidencia ejecutable de RBAC | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\backend\core\tests_scope_access.py` | 14174 | 2026-04-11 23:24:03 | evidencia ejecutable de lectura y escritura scopeada | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\backend\documentos\scope.py` | 2300 | 2026-04-11 23:52:41 | filtrado de scope para Documentos | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\backend\canales\scope.py` | 1053 | 2026-04-12 00:05:05 | filtrado de scope para Canales | leido |

## 3. Deploy y runtime publico

| Ruta absoluta | Tamano | Modificado | Rol dentro del proyecto | Estado de lectura |
|---|---:|---|---|---|
| `D:\Proyectos\LeaseManager\Produccion 1.0\docs\DEPLOY_FRONTEND_VERCEL.md` | 1887 | 2026-04-12 10:01:18 | decision y operacion de deploy frontend | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\docs\DEPLOY_BACKEND_GREENFIELD.md` | 5024 | 2026-04-12 13:02:03 | decision y operacion de deploy backend | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\docs\ROLL_OUT_BACKEND_FRONTEND.md` | 3452 | 2026-04-12 13:09:17 | checklist de conexion frontend/backend | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\backend\railway.web.json` | 276 | 2026-04-12 13:01:50 | config as code del web service Railway | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\backend\railway.worker.json` | 301 | 2026-04-12 12:19:24 | config as code del worker Railway | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\scripts\connect-frontend-to-backend.ps1` | 1954 | 2026-04-12 13:09:17 | helper de upsert y redeploy Vercel | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\frontend\.vercel\project.json` | 128 | 2026-04-12 09:59:21 | enlace local al proyecto Vercel activo | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\backend\health\views.py` | 1680 | 2026-04-10 17:11:23 | health y ready checks del backend publico | leido |

## 4. Paquete de handoff vigente

| Ruta absoluta | Tamano | Modificado | Rol dentro del proyecto | Estado de lectura |
|---|---:|---|---|---|
| `D:\Proyectos\LeaseManager\Produccion 1.0\HANDOFF\00_HANDOFF_INDEX.md` | 8885 | 2026-04-12 17:31:14 | indice y orden de lectura del paquete | leido y actualizado |
| `D:\Proyectos\LeaseManager\Produccion 1.0\HANDOFF\01_CONTEXTO_MAESTRO.md` | 12470 | 2026-04-12 17:32:01 | contexto maestro consolidado | leido y actualizado |
| `D:\Proyectos\LeaseManager\Produccion 1.0\HANDOFF\02_FUENTES_Y_RUTAS.md` | 14134 | 2026-04-12 17:33:04 | inventario clasificado de fuentes | leido y actualizado |
| `D:\Proyectos\LeaseManager\Produccion 1.0\HANDOFF\03_CRONOLOGIA.md` | 3922 | 2026-04-12 17:33:24 | cronologia secuencial del trabajo | leido y actualizado |
| `D:\Proyectos\LeaseManager\Produccion 1.0\HANDOFF\04_DECISIONES_VIGENTES.md` | 5650 | 2026-04-12 17:33:49 | decisiones cerradas, provisorias y descartadas | leido y actualizado |
| `D:\Proyectos\LeaseManager\Produccion 1.0\HANDOFF\05_HALLAZGOS_Y_RIESGOS.md` | 5321 | 2026-04-12 17:34:10 | hallazgos firmes y riesgos abiertos | leido y actualizado |
| `D:\Proyectos\LeaseManager\Produccion 1.0\HANDOFF\06_BORRADOR_ACTUAL.md` | 8781 | 2026-04-12 17:34:47 | base vigente para retomar el entregable | leido y actualizado |
| `D:\Proyectos\LeaseManager\Produccion 1.0\HANDOFF\07_RESPUESTAS_EXTERNAS_LITERAL.md` | 15356 | 2026-04-12 00:27:25 | archivo de respuestas externas literales | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\HANDOFF\08_PENDIENTES_Y_PROXIMOS_PASOS.md` | 4155 | 2026-04-12 17:35:22 | pendientes y siguiente etapa recomendada | leido y actualizado |
| `D:\Proyectos\LeaseManager\Produccion 1.0\HANDOFF\09_BOOTSTRAP_NUEVO_THREAD.txt` | 4722 | 2026-04-12 17:35:22 | prompt de arranque para un nuevo thread | leido y actualizado |
| `D:\Proyectos\LeaseManager\Produccion 1.0\HANDOFF\10_CONTROL_DE_CALIDAD.md` | 3599 | 2026-04-12 17:35:40 | control de calidad del paquete | leido y actualizado |

## 5. Contexto Git verificado

| Contexto | Valor | Rol | Verificado |
|---|---|---|---|
| Git root activo | `D:\Proyectos\LeaseManager\Produccion 1.0` | repo local oficial del greenfield | si |
| HEAD funcional previo al refresh | `9068f7e42cc9be1495ab950d33a0cbb655dca906` | ultimo commit funcional de rollout antes de esta actualizacion documental | si |
| Commit trigger conectado | `385061274b7c145453b995de4dd3b1dcbc715a7f` | rebuild conectado de Vercel/Railway | si |
| Remoto origin | `https://github.com/puigjoaco/LeaseManager.git` | remoto oficial del greenfield | si |
| Remoto legacy historico | `https://github.com/puigjoaco/LeaseManager-legacy.git` | repo historico separado | si |
| Estado del working tree al iniciar este refresh | `HANDOFF ya dirty` | el refresh documental parte sobre un paquete previamente atrasado | si |

## 6. Material no versionado pero relevante para continuidad

Estos elementos no forman parte del inventario versionado anterior, pero fueron constatados en el contexto de trabajo y deben seguir tratandose como estado operativo:

- base local `leasemanager_migration_run_20260409_v7` con datos `TEST LOCAL`;
- backend local disponible en `http://127.0.0.1:8000/api/v1/health/` durante la validacion;
- frontend local disponible en `http://127.0.0.1:5173` durante la validacion;
- frontend publico en `https://leasemanager-backoffice.vercel.app`;
- backend publico en `https://surprising-balance-production.up.railway.app`;
- proyecto Railway `content-friendship` con web `surprising-balance`, worker `spirited-recreation` y Redis online;
- usuarios demo sembrados remotamente para smoke publico;
- configuracion local fuera del repo que volvio a dejar operativo el MCP de Playwright.
