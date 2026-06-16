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
| Frente activo | `stage6-generated-review-chain`. |
| Fuente exacta | worktree `D:/Proyectos/10_ACTIVOS/LeaseManager-stage6-generated-review-chain`, creado sobre `main` `454b7c48`. |
| Brecha activa | La revision responsable de warnings generados debe cerrar en una sola cadena workbooks RLI/CPT, registros empresariales y matriz DDJJ/F22, y despues regenerar dossier, export, checklist y comparador espejo sin borrar warnings ni abrir calculo final. |
| Motivo de prioridad | El mirror proof ya distingue entrada de piloto desde libros cerrados, pero aun quedaba una accion operativa local para registrar revision no sensible de todos los warnings generados y refrescar la cadena anual que decide si la comparacion puede concluir. |
| Worktree | Continuar/cerrar `D:/Proyectos/10_ACTIVOS/LeaseManager-stage6-generated-review-chain`. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `codex/stage6-generated-review-chain`; al cerrar, PR/CI/merge y limpiar worktree. |
| Estado | En desarrollo validado focalmente: `mark_annual_tax_generated_warnings_reviewed` opera dry-run por defecto y solo escribe con `--apply`. Exige `warning_review_ref` no sensible, preserva warnings en payload/hash y refresca dossier/export/checklist/respaldo tributario sin formato oficial, presentacion SII ni calculo tributario final. |
| Gate esperado | Stage 6 debe seguir `classification=parcial` si faltan fuentes externas, bienes raices, validacion experta/oficial o cierre final. Este paquete solo puede desbloquear `generated_artifacts_require_review` cuando la revision responsable local queda trazada. |
| Estado al cerrar paquete | No reabrir prompts de goal, boundary contable de PR #859, gate espejo backend, wrapper Stage 6, corrida controlada AC2024, boundary laboral-previsional DJ1887, selector anual, ownership, respaldo tributario, bienes raices, DDJJ/F22 semantico, Balance General, RLI/CPT/RAI/SAC, revision de warnings RLI/CPT, revision de warnings de matriz DDJJ/F22, revision de warnings de registros empresariales, checklist de warnings pendientes, source bundle anual, F29 no-declaration, evidencia redaccionada de artefactos generados ni EDIG como bloqueo general salvo bug nuevo. Tras cerrar este paquete, el siguiente frente real queda en completar warnings pendientes concretos reportados por Stage 6/mirror proof, comparacion de outputs esperados o fuentes externas autorizables. |
| Bloqueos relacionados | Sin autorizacion o fuente real no se debe presentar SII, declarar calculo tributario final ni afirmar cierre productivo. El bloqueo externo queda como condicion de cierre real/productivo, no como freno para seguir por el siguiente frente seguro. |
| Politica de reanudacion | No reabrir goal prompts, EDIG ni paquetes mergeados. No usar `.env`, secretos, DB real, produccion, SII real ni integraciones externas sin autorizacion explicita. Si falta fuente externa, continuar con preparacion local segura y trazable. |
| Siguiente accion | Completar documentacion, validacion amplia, PR/CI/merge y limpiar `stage6-generated-review-chain`; luego continuar con el siguiente bloqueo concreto de Stage 6/mirror proof, sin usar SII real, `.env`, EDIG ejecutable ni datos externos no autorizados. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
