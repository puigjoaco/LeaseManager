# Manifest

## 1. Archivos fuente y piezas relevantes

| Ruta absoluta | Tamano | Modificado | Rol | Leido o solo referenciado |
|---|---:|---|---|---|
| D:/Proyectos/LeaseManager/Produccion 1.0/AGENTS.md | 6029 | 2026-03-15 23:27:06 | contexto operativo del root activo | leido |
| D:/Proyectos/LeaseManager/Produccion 1.0/README.md | 2572 | 2026-03-16 09:48:39 | contexto del root activo | leido |
| D:/Proyectos/LeaseManager/Produccion 1.0/ORDEN_DE_LECTURA.md | 2838 | 2026-03-15 22:24:13 | orden canonico de lectura | leido |
| D:/Proyectos/LeaseManager/Produccion 1.0/01_Set_Vigente/PRD_CANONICO.md | 50051 | 2026-03-15 21:07:10 | fuente primaria principal | leido |
| D:/Proyectos/LeaseManager/Produccion 1.0/02_ADR_Activos/ADR_ARQUITECTURA_001_BANCA_MULTI_PROVIDER.md | 2385 | 2026-03-15 14:26:43 | ADR activo de recaudacion bancaria | leido |
| D:/Proyectos/LeaseManager/Produccion 1.0/02_ADR_Activos/ADR_ARQUITECTURA_008_CONTABILIDAD_NATIVA.md | 5417 | 2026-03-15 20:54:26 | ADR activo de contabilidad | leido |
| D:/Proyectos/LeaseManager/AGENTS.md | 25373 | 2026-03-14 09:40:00 aprox. | fuente primaria operativa del proyecto general y casos especiales reales | leido |
| D:/Proyectos/LeaseManager/Produccion 1.0/docs/AUDITORIA_DISENO_COMUNIDADES_Y_RECAUDACION_2026-04-05.md | 11965 | 2026-04-05 12:09:08 | auditoria de diseño historicamente decisiva | leido |
| D:/Proyectos/LeaseManager/Produccion 1.0/docs/ESPECIFICACION_TECNICA_FINAL_COMUNIDADES_RECAUDACION_Y_ATRIBUCION.md | 17714 | 2026-04-06 09:34:53 | borrador tecnico vigente / base principal actual | leido |
| D:/Proyectos/LeaseManager/Produccion 1.0/docs/HANDOFF_GREENFIELD_2026-03-22.md | 8759 | 2026-03-22 22:38:42 | pieza procesal historica | leido |
| D:/Proyectos/LeaseManager/Produccion 1.0/migration/transformers.py | 22231 | 2026-04-07 00:10:31 | implementacion del export canonical y defaults de migracion | leido |
| D:/Proyectos/LeaseManager/Produccion 1.0/migration/importers.py | 33445 | 2026-04-06 09:40:44 | implementacion del import canonical y derivacion de mandatos | leido |
| D:/Proyectos/LeaseManager/Produccion 1.0/migration/enrichments.py | 8768 | 2026-04-07 00:10:25 | pieza de trabajo critica con verdad de negocio confirmada por el usuario | leido |
| D:/Proyectos/LeaseManager/Produccion 1.0/migration/bundles/legacy_rows_supabase.json | 537802 | 2026-04-05 23:40:06 | extraccion legacy real via Supabase read-only | leido |
| D:/Proyectos/LeaseManager/Produccion 1.0/migration/bundles/legacy_seed_bundle.regenerated.json | 725504 | 2026-04-06 23:31:54 | bundle canonico vigente regenerado | leido parcialmente / inspeccionado |
| D:/Proyectos/LeaseManager/Produccion 1.0/backend/patrimonio/models.py | 16354 | 2026-04-05 13:08:35 | modelo patrimonial vigente | leido |
| D:/Proyectos/LeaseManager/Produccion 1.0/backend/operacion/models.py | 21465 | 2026-04-05 13:24:17 | modelo operativo vigente | leido |
| D:/Proyectos/LeaseManager/Produccion 1.0/backend/cobranza/models.py | 14294 | 2026-04-05 13:29:27 | modelo de cobranza vigente | leido |
| D:/Proyectos/LeaseManager/Produccion 1.0/backend/cobranza/services.py | 12702 | 2026-04-05 13:29:42 | calculo y distribucion del cobro | leido |
| D:/Proyectos/LeaseManager/Produccion 1.0/backend/conciliacion/services.py | 6529 | 2026-04-05 13:30:29 | conciliacion y refresco de distribucion | leido |
| D:/Proyectos/LeaseManager/Produccion 1.0/backend/contabilidad/services.py | 16913 | 2026-04-05 13:35:10 | eventos contables por distribucion empresa | leido |
| D:/Proyectos/LeaseManager/Produccion 1.0/backend/sii/services.py | 11551 | 2026-04-05 13:32:18 | emision DTE desde distribucion facturable | leido |
| D:/Proyectos/LeaseManager/Produccion 1.0/backend/reporting/services.py | 11785 | 2026-04-05 13:36:09 | reporting financiero por distribucion | leido |
| D:/Proyectos/LeaseManager/Produccion 1.0/backend/audit/services.py | 8872 | 2026-04-06 09:36:07 | resolucion manual comunitaria y representacion designada | leido |
| D:/Proyectos/LeaseManager/Produccion 1.0/backend/audit/views.py | 3132 | 2026-04-05 23:12:10 | endpoint de resolucion manual | leido |
| D:/Proyectos/LeaseManager/Produccion 1.0/backend/audit/serializers.py | 3017 | 2026-04-05 23:48:49 | contrato API de resolucion manual enriquecida | leido |
| D:/Proyectos/LeaseManager/Produccion 1.0/backend/core/tests_migration_pipeline.py | 85585 | 2026-04-07 00:11:13 | evidencia ejecutable del pipeline y enriquecimientos | leido |
| D:/Proyectos/LeaseManager/Produccion 1.0/backend/bundle-inspect-final.db | 1384448 | 2026-04-07 00:15:03 | artefacto de corrida de inspeccion final | leido parcialmente / inspeccionado |
| D:/Proyectos/LeaseManager/.env.production.local | 2731 | 2026-01-11 00:33:36 | contexto sensible local inspeccionado parcialmente para acceso read-only a Supabase | inspeccion parcial, secretos no transcritos |

## 2. Archivos del paquete HANDOFF

| Ruta absoluta | Tamano | Modificado | Rol | Leido o solo referenciado |
|---|---:|---|---|---|
| D:/Proyectos/LeaseManager/Produccion 1.0/HANDOFF/00_HANDOFF_INDEX.md | 4764 | 2026-04-07 00:16:53 | indice del paquete actualizado | leido y actualizado |
| D:/Proyectos/LeaseManager/Produccion 1.0/HANDOFF/01_CONTEXTO_MAESTRO.md | 8123 | 2026-04-07 00:17:36 | contexto consolidado actualizado | leido y actualizado |
| D:/Proyectos/LeaseManager/Produccion 1.0/HANDOFF/02_FUENTES_Y_RUTAS.md | 8478 | 2026-04-07 00:18:18 | inventario de fuentes actualizado | leido y actualizado |
| D:/Proyectos/LeaseManager/Produccion 1.0/HANDOFF/03_CRONOLOGIA.md | 6299 | 2026-04-07 00:18:50 | cronologia lineal actualizada | leido y actualizado |
| D:/Proyectos/LeaseManager/Produccion 1.0/HANDOFF/04_DECISIONES_VIGENTES.md | 3823 | 2026-04-07 00:19:14 | decisiones vigentes actualizadas | leido y actualizado |
| D:/Proyectos/LeaseManager/Produccion 1.0/HANDOFF/05_HALLAZGOS_Y_RIESGOS.md | 3190 | 2026-04-07 00:19:35 | hallazgos y riesgos actualizados | leido y actualizado |
| D:/Proyectos/LeaseManager/Produccion 1.0/HANDOFF/06_BORRADOR_ACTUAL.md | 2427 | 2026-04-07 00:19:55 | borrador principal actualizado | leido y actualizado |
| D:/Proyectos/LeaseManager/Produccion 1.0/HANDOFF/07_RESPUESTAS_EXTERNAS_LITERAL.md | 14540 | 2026-04-07 00:20:48 | respuestas externas literales archivadas | leido y actualizado |
| D:/Proyectos/LeaseManager/Produccion 1.0/HANDOFF/08_PENDIENTES_Y_PROXIMOS_PASOS.md | 3102 | 2026-04-07 00:21:09 | pendientes y proximo paso actualizados | leido y actualizado |
| D:/Proyectos/LeaseManager/Produccion 1.0/HANDOFF/09_BOOTSTRAP_NUEVO_THREAD.txt | 2196 | 2026-04-07 00:21:24 | bootstrap listo para nuevo thread | leido y actualizado |
| D:/Proyectos/LeaseManager/Produccion 1.0/HANDOFF/10_CONTROL_DE_CALIDAD.md | 2605 | 2026-04-07 00:21:40 | control de calidad actualizado | leido y actualizado |
| D:/Proyectos/LeaseManager/Produccion 1.0/HANDOFF/11_MANIFEST.md | 6961 | 2026-04-07 00:22:44 | manifiesto final actualizado | leido y actualizado |
