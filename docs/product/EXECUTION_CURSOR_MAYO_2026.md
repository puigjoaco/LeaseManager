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
| Frente activo | `main-clean-next-stage6-mirror-proof`. |
| Fuente exacta | `main` despues de cerrar `stage6-checklist-pending-warnings`. |
| Brecha activa | `AnnualTaxReviewChecklist` ya no debe mantener en `warning` los items RLI/CPT ni registros empresariales cuando los warnings estan revisados con referencia no sensible: el checklist usa `warnings_pending_review_total` para bloquear y conserva `warnings_total` solo como auditoria. El siguiente bloqueo real queda en brechas concretas de Stage 6/mirror proof, evidencia de artefactos generados, comparacion de outputs esperados o fuentes externas autorizadas. |
| Motivo de prioridad | La prueba controlada AC2024/AT2025 ya distingue warnings totales, revisados y pendientes en workbooks, matriz y registros empresariales. El checklist queda alineado para no reabrir warnings ya revisados ni aceptar referencias sensibles como revision valida. |
| Worktree | No debe quedar worktree tactico activo de `stage6-checklist-pending-warnings` tras el merge. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `main` limpio para el siguiente paquete; abrir nuevo worktree `codex/...` solo si el siguiente frente requiere cambios. |
| Estado | En SQLite local, `audit_stage6_renta_anual_readiness` sigue `classification=parcial`, `ready_for_stage6_renta_anual=false` para fuente local. Esto no declara calculo tributario final, formato oficial ni presentacion SII; solo elimina un bloqueo falso del checklist cuando ya no existen warnings pendientes de revision. |
| Gate esperado | Para AC2024/AT2025 controlado o autorizado, usar `scripts/run-stage6-mirror-proof-gate.ps1`; con `-FailOnIncomplete` solo si se exige `ready_for_objective_completion=true`. El siguiente frente util debe salir de trazabilidad, stage cards y estado real de `main` limpio. |
| Estado al cerrar paquete | No reabrir prompts de goal, boundary contable de PR #859, gate espejo backend, wrapper Stage 6, corrida controlada AC2024, boundary laboral-previsional DJ1887, selector anual, ownership, respaldo tributario, bienes raices, DDJJ/F22 semantico, Balance General, RLI/CPT/RAI/SAC, revision de warnings RLI/CPT, revision de warnings de matriz DDJJ/F22, revision de warnings de registros empresariales, checklist de warnings pendientes, source bundle anual, F29 no-declaration ni EDIG como bloqueo general salvo bug nuevo. Tras cerrar este paquete, el siguiente frente real queda en completar brechas concretas reportadas por Stage 6/mirror proof, especialmente evidencia de artefactos generados y comparacion de outputs esperados. |
| Bloqueos relacionados | Sin autorizacion o fuente real no se debe presentar SII, declarar calculo tributario final ni afirmar cierre productivo. El bloqueo externo queda como condicion de cierre real/productivo, no como freno para seguir por el siguiente frente seguro. |
| Politica de reanudacion | No reabrir goal prompts, EDIG ni paquetes mergeados. No usar `.env`, secretos, DB real, produccion, SII real ni integraciones externas sin autorizacion explicita. Si falta fuente externa, continuar con preparacion local segura y trazable. |
| Siguiente accion | Continuar con Stage 6/mirror proof desde el estado real de `main`: revisar blockers vigentes de evidencia de artefactos generados, comparacion de outputs esperados y fuentes externas autorizables, sin usar SII real, `.env`, EDIG ejecutable ni datos externos no autorizados. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
