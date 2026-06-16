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
| Frente activo | `main-clean-next-annual-review`. |
| Fuente exacta | `main` despues de cerrar `stage6-preserve-f29-no-declaration`. |
| Brecha activa | El mirror anual AC2024/AT2025 conserva meses F29 sin declaracion al regenerar `MonthlyTaxFact`; el progreso contable/renta tambien exige `AnnualTaxSourceBundle` congelado para contar `annual_process`. El siguiente bloqueo real queda en revision de warnings, bienes raices y comparacion semantica, no en F29 ni en generar `ProcesoRentaAnual` huerfano. |
| Motivo de prioridad | La prueba controlada AC2024/AT2025 ya puede cargar 12 meses, generar `ProcesoRentaAnual` trazado a source bundle congelado, balance anual, RLI/CPT, dossier y export local, manteniendo F29 12/12 despues del mirror. |
| Worktree | No debe quedar worktree tactico activo de `stage6-preserve-f29-no-declaration` tras el merge. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `main` limpio para el siguiente paquete; abrir nuevo worktree `codex/...` solo si el siguiente frente requiere cambios. |
| Estado | En SQLite local controlada nueva, `audit_company_accounting_progress` queda `classification=preparado`, `progress_percent=100`, `ready_for_company_accounting_review=true`, `annual_process` trazado por source bundle congelado y F29 12/12 despues de `run_annual_tax_controlled_mirror`. `audit_stage6_renta_anual_readiness` y `audit_annual_tax_mirror_proof` siguen `parcial`; esto no declara contabilidad autonoma, calculo tributario final ni presentacion SII. |
| Gate esperado | Para AC2024/AT2025 controlado o autorizado, usar `scripts/run-stage6-mirror-proof-gate.ps1`; con `-FailOnIncomplete` solo si se exige `ready_for_objective_completion=true`. El siguiente frente util debe salir de trazabilidad, stage cards y estado real de `main` limpio. |
| Estado al cerrar paquete | No reabrir prompts de goal, boundary contable de PR #859, gate espejo backend, wrapper Stage 6, corrida controlada AC2024, boundary laboral-previsional DJ1887, selector anual, ownership, respaldo tributario, bienes raices, DDJJ/F22 semantico, Balance General, RLI/CPT/RAI/SAC, revision de warnings RLI/CPT, revision de warnings de matriz DDJJ/F22, source bundle anual, F29 no-declaration ni EDIG como bloqueo general salvo bug nuevo. Tras cerrar este paquete, el siguiente frente real de Inmobiliaria Puig queda en revisar warnings pendientes y completar brechas concretas reportadas por Stage 6/mirror proof. |
| Bloqueos relacionados | Sin autorizacion o fuente real no se debe presentar SII, declarar calculo tributario final ni afirmar cierre productivo. El bloqueo externo queda como condicion de cierre real/productivo, no como freno para seguir por el siguiente frente seguro. |
| Politica de reanudacion | No reabrir goal prompts, EDIG ni paquetes mergeados. No usar `.env`, secretos, DB real, produccion, SII real ni integraciones externas sin autorizacion explicita. Si falta fuente externa, continuar con preparacion local segura y trazable. |
| Siguiente accion | Continuar con Stage 6/mirror proof: `enterprise_register_movement_warning_review_required`, `real_estate_item_missing`, revision de matriz/dossier/export/checklist y comparacion semantica de outputs esperados, sin usar SII real, `.env`, EDIG ejecutable ni datos externos no autorizados. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
