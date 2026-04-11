# Manifest

Ultima actualizacion del manifest: 2026-04-11

Nota metodologica:

- este inventario lista los archivos clave efectivamente usados para retomar el trabajo actual;
- cuando un archivo sensible fue abierto solo para confirmar contexto operativo, se marca como `inspeccion parcial`;
- este archivo no se autoenumera con tamano y fecha dentro de su propia tabla para evitar inconsistencia autorreferencial.

## 1. Fuentes primarias y operativas clave

| Ruta absoluta | Rol dentro del proyecto | Estado de lectura |
|---|---|---|
| `D:\Proyectos\LeaseManager\Produccion 1.0\README.md` | contexto general del root activo | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\AGENTS.md` | instrucciones operativas del greenfield activo | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\01_Set_Vigente\PRD_CANONICO.md` | fuente primaria canonica del producto | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\02_ADR_Activos\ADR_ARQUITECTURA_001_BANCA_MULTI_PROVIDER.md` | decision arquitectonica activa de banca | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\02_ADR_Activos\ADR_ARQUITECTURA_008_CONTABILIDAD_NATIVA.md` | decision arquitectonica activa de contabilidad | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\03_Ejecucion_Tecnica\ROADMAP_TECNICO.md` | roadmap tecnico vigente | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\03_Ejecucion_Tecnica\MODULOS_Y_DEPENDENCIAS.md` | mapa de modulos y dependencias | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\docs\ESPECIFICACION_TECNICA_FINAL_COMUNIDADES_RECAUDACION_Y_ATRIBUCION.md` | base tecnica del subdominio comunitario ya cerrado | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\docs\MIGRATION_RUNBOOK.md` | runbook operativo de migracion local | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\docs\SUPABASE_STAGING_PLAYBOOK.md` | playbook de staging Supabase | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\infra\docker-compose.yml` | infraestructura local de PostgreSQL y Redis | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\backend\.env` | runtime local activo del backend | inspeccion parcial |
| `D:\Proyectos\LeaseManager\Produccion 1.0\backend\.env.supabase-staging.local` | runtime local para staging Supabase | inspeccion parcial |

## 2. Implementacion viva y evidencia ejecutable

| Ruta absoluta | Rol dentro del proyecto | Estado de lectura |
|---|---|---|
| `D:\Proyectos\LeaseManager\Produccion 1.0\frontend\src\App.tsx` | implementacion viva del backoffice multiworkspace | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\frontend\src\App.css` | soporte visual de la app actual | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\backend\core\permissions.py` | politica RBAC backend vigente | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\backend\core\scope_access.py` | helper central de filtrado por scope | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\backend\core\management\commands\seed_demo_access.py` | seed reproducible de usuarios/roles/scopes demo | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\backend\core\tests_permissions.py` | evidencia ejecutable de RBAC | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\backend\core\tests_scope_access.py` | evidencia ejecutable de lectura y escritura scopeada | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\migration\README.md` | guia vigente del pipeline de migracion | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\migration\orchestration.py` | helper de orquestacion con sanitizacion del target | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\migration\bundles\supabase_staging_verification_2026-04-10.json` | evidencia de verificacion en staging | leido |
| `D:\Proyectos\LeaseManager\Produccion 1.0\migration\bundles\verify_current_migration_target_supabase.json` | evidencia validada del verificador reusable | leido |

## 3. Paquete de handoff vigente

| Ruta absoluta | Rol dentro del proyecto | Estado de lectura |
|---|---|---|
| `D:\Proyectos\LeaseManager\Produccion 1.0\HANDOFF\00_HANDOFF_INDEX.md` | indice y orden de lectura del paquete | leido y actualizado |
| `D:\Proyectos\LeaseManager\Produccion 1.0\HANDOFF\01_CONTEXTO_MAESTRO.md` | contexto maestro consolidado | leido y actualizado |
| `D:\Proyectos\LeaseManager\Produccion 1.0\HANDOFF\02_FUENTES_Y_RUTAS.md` | inventario clasificado de fuentes | leido y actualizado |
| `D:\Proyectos\LeaseManager\Produccion 1.0\HANDOFF\03_CRONOLOGIA.md` | cronologia secuencial del trabajo | leido y actualizado |
| `D:\Proyectos\LeaseManager\Produccion 1.0\HANDOFF\04_DECISIONES_VIGENTES.md` | decisiones cerradas, provisorias y descartadas | leido y actualizado |
| `D:\Proyectos\LeaseManager\Produccion 1.0\HANDOFF\05_HALLAZGOS_Y_RIESGOS.md` | hallazgos firmes y riesgos abiertos | leido y actualizado |
| `D:\Proyectos\LeaseManager\Produccion 1.0\HANDOFF\06_BORRADOR_ACTUAL.md` | base vigente para retomar el entregable | leido y actualizado |
| `D:\Proyectos\LeaseManager\Produccion 1.0\HANDOFF\07_RESPUESTAS_EXTERNAS_LITERAL.md` | archivo de respuestas externas literales | leido y actualizado |
| `D:\Proyectos\LeaseManager\Produccion 1.0\HANDOFF\08_PENDIENTES_Y_PROXIMOS_PASOS.md` | pendientes y siguiente etapa recomendada | leido y actualizado |
| `D:\Proyectos\LeaseManager\Produccion 1.0\HANDOFF\09_BOOTSTRAP_NUEVO_THREAD.txt` | prompt de arranque para un nuevo thread | leido y actualizado |
| `D:\Proyectos\LeaseManager\Produccion 1.0\HANDOFF\10_CONTROL_DE_CALIDAD.md` | control de calidad del paquete | leido y actualizado |
| `D:\Proyectos\LeaseManager\Produccion 1.0\HANDOFF\11_MANIFEST.md` | manifiesto final de archivos clave | leido y actualizado |

## 4. Contexto Git verificado

| Contexto | Valor | Verificado |
|---|---|---|
| Git root activo | `D:\Proyectos\LeaseManager\Produccion 1.0` | si |
| HEAD actual | `bdde84300fc2af430205de75a9181847abe00a68` | si |
| Remoto origin | `https://github.com/puigjoaco/LeaseManager.git` | si |
| Remoto legacy historico | `https://github.com/puigjoaco/LeaseManager-legacy.git` | si |
| Estado del working tree al cerrar este refresh | `clean` esperado tras publicar este paquete | si |

## 5. Material no versionado pero relevante para continuidad

Estos elementos no forman parte del inventario versionado anterior, pero fueron constatados en el contexto de trabajo y deben seguir tratandose como estado local:

- base local `leasemanager_migration_run_20260409_v7` con datos `TEST LOCAL`;
- contenedores Docker `leasemanager-postgres` y `leasemanager-redis`;
- backend local disponible en `http://127.0.0.1:8000/api/v1/health/` durante la validacion;
- frontend local disponible en `http://127.0.0.1:5173` durante la validacion;
- usuario admin de desarrollo creado localmente para pruebas, no versionado;
- usuarios demo reproducibles (`demo-admin`, `demo-operador`, `demo-revisor`, `demo-socio`) creados localmente para validacion RBAC/scope;
- MCP de Playwright con falla de permisos sobre `C:\Windows\System32\.playwright-mcp`.
