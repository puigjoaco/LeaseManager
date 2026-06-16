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
| Frente activo | `stage6-document-semantic-filter`. |
| Fuente exacta | worktree `D:/Proyectos/10_ACTIVOS/LeaseManager-stage6-document-semantic-filter` desde `main` `6074590d`. |
| Brecha activa | La prueba espejo AC2024/AT2025 conserva miles de errores de extraccion sobre archivos historicos, baseline o no decisivos, aun cuando las DDJJ aceptadas, F22, balance, registros y documentos comparados estan presentes. Esos errores deben seguir como diagnostico, pero no bloquear identidad/semantica ni dejar `value_extractors_partial` si la cobertura decisiva esta lista. |
| Motivo de prioridad | El gate espejo debe diferenciar errores de extraccion bloqueantes de ruido historico. Si no lo hace, reaparece un bloqueo falso y se pierde foco en los bloqueos reales: revision responsable de artefactos, fuente bienes raices, source documentation/architecture proof o validacion externa. |
| Worktree | Continuar/cerrar `D:/Proyectos/10_ACTIVOS/LeaseManager-stage6-document-semantic-filter`. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `codex/stage6-document-semantic-filter`; al cerrar, PR/CI/merge y limpiar worktree. |
| Estado | En pruebas locales, `compare_annual_tax_expected_outputs` agrega `blocking_extraction_errors_total` para identidad y semantica documental. Los errores de extraccion permanecen en `extraction_errors`, pero solo bloquean si falta la evidencia requerida de su propia familia documental o registro. Esto no declara calculo tributario final, formato oficial ni presentacion SII. |
| Gate esperado | Para AC2024/AT2025 controlado o autorizado, usar `scripts/run-stage6-mirror-proof-gate.ps1`; con `-FailOnIncomplete` solo si se exige `ready_for_objective_completion=true`. Si la ruta fuente completa no esta disponible, contrastar contra el JSON previo de comparacion y tests focales/impactados, dejando explicitada esa limitacion. |
| Estado al cerrar paquete | No reabrir prompts de goal, boundary contable de PR #859, gate espejo backend, wrapper Stage 6, corrida controlada AC2024, boundary laboral-previsional DJ1887, selector anual, ownership, respaldo tributario, bienes raices, DDJJ/F22 semantico, Balance General, RLI/CPT/RAI/SAC, revision de warnings RLI/CPT, revision de warnings de matriz DDJJ/F22, revision de warnings de registros empresariales, checklist de warnings pendientes, source bundle anual, F29 no-declaration, evidencia redaccionada de artefactos generados ni EDIG como bloqueo general salvo bug nuevo. Tras cerrar este paquete, el siguiente frente real queda en completar warnings pendientes concretos reportados por Stage 6/mirror proof, comparacion de valores de outputs esperados o fuentes externas autorizables. |
| Bloqueos relacionados | Sin autorizacion o fuente real no se debe presentar SII, declarar calculo tributario final ni afirmar cierre productivo. El bloqueo externo queda como condicion de cierre real/productivo, no como freno para seguir por el siguiente frente seguro. |
| Politica de reanudacion | No reabrir goal prompts, EDIG ni paquetes mergeados. No usar `.env`, secretos, DB real, produccion, SII real ni integraciones externas sin autorizacion explicita. Si falta fuente externa, continuar con preparacion local segura y trazable. |
| Siguiente accion | Validar, documentar, PR/CI/merge y limpiar `stage6-document-semantic-filter`; luego continuar con el siguiente warning/bloqueo concreto de Stage 6/mirror proof, sin usar SII real, `.env`, EDIG ejecutable ni datos externos no autorizados. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
