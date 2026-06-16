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
| Frente activo | `main-clean-next-annual-process`. |
| Fuente exacta | `main` despues de cerrar `company-progress-f29-no-declaration`. |
| Brecha activa | La cobertura F29 mensual controlada para Inmobiliaria Puig AC2024/AT2025 ya distingue meses sin declaracion (`no_aplica` + `no_declaration=true`) de F29 faltante. |
| Motivo de prioridad | La prueba controlada AC2024/AT2025 ya cargo 12 cierres/libros/balances y 12 `MonthlyTaxFact`; febrero y diciembre no deben bloquear `f29_monthly` si estan normalizados como meses sin declaracion. |
| Worktree | No debe quedar worktree tactico activo de `company-progress-f29-no-declaration` tras el merge. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `main` limpio para el siguiente paquete; abrir nuevo worktree `codex/...` solo si el siguiente frente requiere cambios. |
| Estado | El auditor de progreso cuenta F29 preparados y meses con `MonthlyTaxFact` normalizado cuyo F29 esta `no_aplica` y `no_declaration=true`. En el caso AC2024/AT2025, esos meses dejan de ser ausencia documental y el siguiente bloqueo operativo pasa a `annual_process` cuando la fuente controlada los carga normalizados. Esto no declara contabilidad autonoma, calculo tributario final ni presentacion SII. |
| Gate esperado | Para AC2024/AT2025 controlado o autorizado, usar `scripts/run-stage6-mirror-proof-gate.ps1`; con `-FailOnIncomplete` solo si se exige `ready_for_objective_completion=true`. El siguiente frente util debe salir de trazabilidad, stage cards y estado real de `main` limpio. |
| Estado al cerrar paquete | No reabrir prompts de goal, boundary contable de PR #859, gate espejo backend, wrapper Stage 6, corrida controlada AC2024, boundary laboral-previsional DJ1887, selector anual, ownership, respaldo tributario, bienes raices, DDJJ/F22 semantico, Balance General, RLI/CPT/RAI/SAC, revision de warnings RLI/CPT, revision de warnings de matriz DDJJ/F22 ni EDIG como bloqueo general salvo bug nuevo. Tras cerrar este paquete, el siguiente frente real de Inmobiliaria Puig queda en generar/revisar capa anual (`ProcesoRentaAnual`) con ownership controlado o evidencia equivalente. |
| Bloqueos relacionados | Sin autorizacion o fuente real no se debe presentar SII, declarar calculo tributario final ni afirmar cierre productivo. El bloqueo externo queda como condicion de cierre real/productivo, no como freno para seguir por el siguiente frente seguro. |
| Politica de reanudacion | No reabrir goal prompts, EDIG ni paquetes mergeados. No usar `.env`, secretos, DB real, produccion, SII real ni integraciones externas sin autorizacion explicita. Si falta fuente externa, continuar con preparacion local segura y trazable. |
| Siguiente accion | Continuar con el frente real `annual_process`/ownership controlado para convertir la base mensual AC2024/AT2025 en proceso anual revisable, sin usar SII real, `.env`, EDIG ejecutable ni datos externos no autorizados. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
