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
| Frente activo | `stage6-generated-artifact-evidence`. |
| Fuente exacta | worktree `D:/Proyectos/10_ACTIVOS/LeaseManager-stage6-generated-artifact-evidence` desde `main` `fbb1dda6`. |
| Brecha activa | La prueba espejo necesita evidencia redaccionada de artefactos generados para ubicar el bloqueo `generated_artifacts_require_review`, y las revisiones de warnings no deben aceptar refs sensibles heredadas como evidencia valida. |
| Motivo de prioridad | El gate mirror AC2024/AT2025 ya compara cobertura, identidad, semantica documental y valores; el bloqueo restante debe indicar que artefacto generado falta revisar sin exponer payloads ni permitir que URLs/tokens despejen warnings. |
| Worktree | Continuar/cerrar `D:/Proyectos/10_ACTIVOS/LeaseManager-stage6-generated-artifact-evidence`. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `codex/stage6-generated-artifact-evidence`; al cerrar, PR/CI/merge y limpiar worktree. |
| Estado | En pruebas locales, `comparison_generated_artifact_evidence` queda disponible con ids, hashes, conteos y refs redactadas; refs sensibles de warning_review_ref en workbooks/matriz se tratan como pendientes y bloquean readiness. Esto no declara calculo tributario final, formato oficial ni presentacion SII. |
| Gate esperado | Para AC2024/AT2025 controlado o autorizado, usar `scripts/run-stage6-mirror-proof-gate.ps1`; con `-FailOnIncomplete` solo si se exige `ready_for_objective_completion=true`. El siguiente frente util debe salir de trazabilidad, stage cards y estado real de `main` limpio. |
| Estado al cerrar paquete | No reabrir prompts de goal, boundary contable de PR #859, gate espejo backend, wrapper Stage 6, corrida controlada AC2024, boundary laboral-previsional DJ1887, selector anual, ownership, respaldo tributario, bienes raices, DDJJ/F22 semantico, Balance General, RLI/CPT/RAI/SAC, revision de warnings RLI/CPT, revision de warnings de matriz DDJJ/F22, revision de warnings de registros empresariales, checklist de warnings pendientes, source bundle anual, F29 no-declaration, evidencia redaccionada de artefactos generados ni EDIG como bloqueo general salvo bug nuevo. Tras cerrar este paquete, el siguiente frente real queda en completar warnings pendientes concretos reportados por Stage 6/mirror proof, comparacion de outputs esperados o fuentes externas autorizables. |
| Bloqueos relacionados | Sin autorizacion o fuente real no se debe presentar SII, declarar calculo tributario final ni afirmar cierre productivo. El bloqueo externo queda como condicion de cierre real/productivo, no como freno para seguir por el siguiente frente seguro. |
| Politica de reanudacion | No reabrir goal prompts, EDIG ni paquetes mergeados. No usar `.env`, secretos, DB real, produccion, SII real ni integraciones externas sin autorizacion explicita. Si falta fuente externa, continuar con preparacion local segura y trazable. |
| Siguiente accion | Validar, documentar, PR/CI/merge y limpiar `stage6-generated-artifact-evidence`; luego continuar con el siguiente warning/bloqueo concreto de Stage 6/mirror proof, sin usar SII real, `.env`, EDIG ejecutable ni datos externos no autorizados. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
