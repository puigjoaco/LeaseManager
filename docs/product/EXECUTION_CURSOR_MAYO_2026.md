# Cursor operativo - mayo 2026

Este archivo fija el frente activo de ejecucion. No reemplaza al PRD, AGENTS,
fuente de verdad, arquitectura, matriz, stage cards, evidencia ni bloqueos. Su
funcion es evitar que una reanudacion convierta contexto auxiliar en tarea
nueva.

## Regla de uso

- Antes de abrir o continuar cambios no triviales, leer este cursor.
- Confirmar el estado real con `git status --short --branch` y
  `git worktree list`.
- Si existe un worktree tactico sucio, se debe terminar, pausar de forma
  explicita en este cursor o descartar con instruccion segura antes de abrir un
  frente distinto.
- Solo el estado real del repo y este cursor definen la siguiente accion
  operativa.
- El contexto auxiliar no autoriza secretos, no abre gates y no crea tareas
  nuevas salvo solicitud textual actual del usuario.

## Cursor actual

| Campo | Valor |
| --- | --- |
| Frente activo | `ac2024-ownership-patch`. |
| Fuente exacta | `main` posterior al merge de PR #856 (`ac2024-mirror-source-bundle`) y al paquete visual/local de ownership. |
| Brecha activa | Cerrado el tramo local AC2024/AT2025: selector anual acotado al ano comercial, ownership controlado, respaldo tributario PDF y bienes raices/contribuciones controladas. El paquete debe cerrarse con validacion, commit, PR, CI y merge. |
| Motivo de prioridad | Deja probada la arquitectura contabilidad mensual -> capa anual -> ownership -> bienes raices -> DDJJ/F22/dossier/export/checklist para Inmobiliaria Puig AC2024/AT2025 sin usar SII real, EDIG ni outputs finales como input. |
| Worktree | Activo tactico `D:/Proyectos/10_ACTIVOS/LeaseManager-ac2024-ownership-patch` en rama `codex/ac2024-ownership-patch`; `main` queda como base limpia. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `codex/ac2024-ownership-patch`; cerrar con PR/CI/merge cuando el selector, evidencia y docs queden validados. |
| Estado | Auditor empresa/ano disponible por comando y expuesto en Reporting como `contabilidad/progreso-empresa/`; candidatos disponibles en `contabilidad/candidatos-progreso-empresa/`. Para Inmobiliaria Puig AC2024/AT2025 se agrego manifiesto read-only, plan de carga controlada, template de paquete normalizado, auditor de paquete, draft de valores, writer DB local `apply_annual_tax_controlled_db_load`, run anual controlado `run_annual_tax_controlled_mirror`, comparador de cobertura/identidad/valores/semantica documental `compare_annual_tax_expected_outputs --source-root` y evidencia SQLite local ignorada. Balance General, RLI/CPT/RAI, DDJJ y F22 finales quedan como comparacion, no como calculo. El manifiesto real ahora exige `ownership_source_input`: confirma RCV 12/12, F29 controlado 12/12, libros anuales, DDJJ, F22 y registros tributarios esperados completos, pero `ready_for_mirror_source_bundle=false` porque `ownership_source_present=false`; falta fuente societaria independiente. El manifiesto tambien clasifica escrituras/extractos/inscripciones/Diario Oficial de contexto societario como `ownership_source_candidate` de soporte, no input: corrida real detecta 15 candidatos y mantiene `ownership_source_present=false`. `review_annual_tax_ownership_candidates` revisa esos candidatos sin guardar texto crudo/RUTs/nombres; corrida real confirma `text_extractable_files_total=0`, 10 candidatos legales para OCR/revision manual, 3 documentos nulos/sin efecto excluidos y 2 aportes/propiedades como soporte. `build_annual_tax_ownership_snapshot_template` genera desde esa revision un template real con 10 `candidate_sources`, `participants=[]`, `ready_for_controlled_db_load=false` y `can_patch_controlled_db_load_package_after_manual_completion=true`. `build_annual_tax_ownership_visual_review_packet` renderiza localmente esos 10 candidatos bajo `local-evidence`: 19 paginas PNG, 0 errores, `ready_for_manual_visual_review=true`, `ready_for_controlled_db_load=false`; las imagenes pueden contener datos sensibles y no se versionan. El siguiente paso es revisar/OCR esas 19 paginas y completar el template con socios/porcentajes/vigencias/evidencia para producir snapshot ownership controlado AC2024. El template real confirma refs mensuales completas, libros anuales presentes y F29 febrero/diciembre `no_aplica`; el draft real extrae Libro Diario, Libro Mayor, Libro Inventario, F29 y remuneraciones desde fuentes permitidas, rellena 180 campos y queda `ready_for_db_writer=true`. El auditor ahora separa writer mensual de generacion anual: el draft real v3 mantiene `ready_for_annual_generation=false` por `ownership_snapshot_missing` (`$.ownership`). El writer acepta `ownership` como snapshot patrimonial controlado para materializar socios/participaciones y alimentar RETIROS/DIVIDENDOS sin inferir porcentajes desde cuentas de retiro ni outputs finales; para la fuente AC2024 real queda pendiente localizar o cargar esa fuente societaria independiente. El run anual crea capacidades DDJJ/F22 locales, TaxYearRuleSet/mappings/layouts, source bundle `snapshot_controlado`, ProcesoRentaAnual, DDJJ/F22, matriz, dossier, export y checklist. La normalizacion genera 44 lineas de balance anual, 7 lineas workbook RLI/CPT desde Libro Inventario/resultado contable y 9 movimientos de registros empresariales; separa lineas soporte de lineas comparables por `source_payload.expected_output_artifacts`. El draft fusiona Libro Inventario con totales anuales de Libro Mayor para conservar sumas/saldos por cuenta, y el extractor de valores esperados corrige la falsa fusion de tokens PDF. La comparacion v5 confirma cobertura, identidad, semantica documental DDJJ/F22 y valores comparables: 7/7 documentos DDJJ/F22, 138/138 targets de valores y 0 faltantes, sin guardar texto bruto, folios crudos ni usar outputs finales como input. Gate Etapa 6 sobre esa DB sigue `classification=parcial`, `ready_for_stage6_renta_anual=false` por fuente patrimonial pendiente, revision de artefactos generados/responsable, bienes raices, matriz/dossier/export/checklist, respaldo tributario y gates finales. |
| Estado actualizado | PR #856 ya esta mergeado en `main`. En este worktree el selector de `annual_ledger_input` fue corregido para priorizar `commercial_year` y rutas canonicas. La regeneracion real AC2024/AT2025 queda con 180 campos, 0 errores de extraccion y `ready_for_db_writer=true`. Con paquete local ignorado que incluye `ownership` y `real_estate` controlados, `apply_annual_tax_controlled_db_load --apply` carga 12 meses, 1 participante y 1 propiedad/contribucion; `run_annual_tax_controlled_mirror --apply` genera ProcesoRentaAnual, DDJJ/F22 preparados, matriz, dossier, export, checklist, respaldo tributario PDF controlado y `AnnualRealEstateItem` con source bundle `snapshot_controlado`. Gate Etapa 6 sobre `ac2024_real_estate_patch_v1.sqlite3` queda `classification=resuelto_confirmado`, `ready_for_stage6_renta_anual=true`, sin issues. Esto prueba arquitectura local controlada; no es presentacion SII real ni calculo tributario final. |
| Gate esperado | Cargar candidatos en Reporting, elegir empresa/ano, y ejecutar `audit_company_accounting_progress --empresa-id <id> --fiscal-year <ano>` o consultar Reporting con `empresa_id` y `fiscal_year` contra DB local/controlada o fuente autorizada. El JSON puede guardarse solo bajo `local-evidence/`. |
| Estado al cerrar paquete | Auditor, candidatos, exposicion Reporting y boundary de regimen soportado integrados; no reabrir esos paquetes salvo bug nuevo. |
| Bloqueos relacionados | Sin empresa/ano/fuente no se puede afirmar avance real de una empresa. Registrar esa falta una vez y seguir solo con trabajo seguro que no dependa de datos reales. |
| Politica de reanudacion | No reabrir goal prompts, EDIG ni paquetes ya mergeados. Si el usuario no entrega empresa/fuente, continuar con el siguiente paquete seguro desbloqueado sin afirmar avance real de una empresa. |
| Siguiente accion | Cerrar validaciones amplias, commit, PR/CI/merge de `codex/ac2024-ownership-patch`. No reabrir selector anual, ownership, respaldo tributario, bienes raices, DDJJ/F22 semantico, Balance General, RLI/CPT/RAI/SAC, EDIG ni goal prompts como bloqueo general salvo bug nuevo. El siguiente frente, despues del merge, debe ser revision responsable/fuente autorizada o el proximo frente trazable desbloqueado. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
