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
| Frente activo | `stage6-labor-source-ref-draft`. |
| Fuente exacta | worktree `D:/Proyectos/10_ACTIVOS/LeaseManager-stage6-labor-source-ref-draft`, creado sobre `main` `6f736ca1`. |
| Brecha activa | La prueba espejo AC2024/AT2025 ya materializa libros, F29, remuneraciones mensuales y bienes raices, pero el draft no consolidaba `labor_previsional.source_ref` anual cuando existian multiples `payroll_support` esperados. |
| Motivo de prioridad | Es el ultimo bloqueo local del paquete controlado antes de separar correctamente DB writer (`ready`) de generacion anual (`ownership` pendiente). No requiere SII real, `.env`, EDIG ejecutable, DB real ni outputs finales como input. |
| Worktree | Continuar/cerrar `D:/Proyectos/10_ACTIVOS/LeaseManager-stage6-labor-source-ref-draft`. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `codex/stage6-labor-source-ref-draft`; al cerrar, PR/CI/merge y limpiar worktree. |
| Estado | En evidencia real post-fix AC2024/AT2025, el manifiesto inventaria 11085 archivos: 611 inputs, 1492 soportes y 8982 outputs esperados. `build_annual_tax_controlled_values_draft` revisa 112 respaldos laborales, genera `labor_previsional.source_ref`, mantiene `final_tax_calculation=false`, materializa 6 bienes raices y deja `ready_for_db_writer=true` sin usar outputs finales como input. |
| Gate esperado | Etapa 6/mirror proof sigue `classification=parcial`: `ready_for_annual_generation=false` por `ownership_snapshot_missing`. Esto es condicion de cierre/generacion anual, no bloqueo para tener el paquete controlado de entrada preparado. |
| Estado al cerrar paquete | No reabrir Compliance #879, filtro #880, union de tokens #881, hash de registros #882, bienes raices #883, paquetes Stage 6 ya mergeados ni prompts de goal. El siguiente frente real debe completar/revisar `ownership` controlado antes de aplicar bienes raices y ejecutar mirror anual completo en el piloto real. |
| Bloqueos relacionados | `ownership_source_missing` en el manifiesto y `ownership_snapshot_missing` en readiness anual. Existen candidatos legales/OCR, pero todavia no hay snapshot controlado de socios/participaciones vigente AC2024. |
| Politica de reanudacion | No usar `.env`, secretos, DB real, produccion, SII real, EDIG ejecutable ni integraciones externas sin autorizacion explicita. Las salidas F22/DDJJ/Balance/RLI/CPT/RAI/SAC esperadas son comparacion externa read-only, nunca input de calculo. |
| Siguiente accion | Validar, PR/CI/merge y limpiar `stage6-labor-source-ref-draft`; luego continuar con snapshot `ownership` controlado/OCR-revision como siguiente brecha real para acercarse al objetivo de equivalencia AC2024/AT2025. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
