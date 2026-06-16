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
| Frente activo | `stage6-value-error-filter`. |
| Fuente exacta | worktree `D:/Proyectos/10_ACTIVOS/LeaseManager-stage6-value-error-filter`, creado sobre `main` `df7c4cbb`. |
| Brecha activa | El comparador espejo AC2024/AT2025 trata cualquier error de extraccion de valores como bloqueo, aunque sea historico/no decisivo y exista otro output extraible para el mismo par `category/artifact_key`. |
| Motivo de prioridad | La arquitectura de renta anual debe distinguir falso bloqueo tecnico de brecha real. En la comparacion post revision generada hay 5 errores de extraccion de valores, pero el resultado util es que 136 targets siguen faltando; el bloqueo debe quedar en mismatch/extractor incompleto, no en lector historico. |
| Worktree | Continuar/cerrar `D:/Proyectos/10_ACTIVOS/LeaseManager-stage6-value-error-filter`. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `codex/stage6-value-error-filter`; al cerrar, PR/CI/merge y limpiar worktree. |
| Estado | En desarrollo validado focalmente: `extract_expected_output_value_signals` expone `blocking_extraction_errors_total`; errores no decisivos quedan registrados pero no bloquean cuando ya existe una fuente extraible para el mismo par de comparacion. Contraste local AC2024/AT2025: `extraction_errors_total=5`, `blocking_extraction_errors_total=0`, `missing_targets_total=136`. |
| Gate esperado | Etapa 6 sigue `classification=parcial`; este paquete no corrige los 136 targets faltantes, no usa outputs finales como input, no abre SII real, no declara igualdad numerica ni calculo tributario final. |
| Estado al cerrar paquete | No reabrir Compliance #879, paquetes Stage 6 ya mergeados ni prompts de goal. El siguiente frente real debe tomar el primer blocker concreto que quede en mirror proof: targets faltantes, bienes raices, registros empresariales invalidos o soporte tributario, segun evidencia actual. |
| Bloqueos relacionados | La comparacion AC2024/AT2025 sigue bloqueada por `expected_output_value_mismatch` y `expected_output_value_extractors_missing`; esos bloqueos son de contenido/arquitectura de valores, no de permiso externo ni de `.env`. |
| Politica de reanudacion | No usar `.env`, secretos, DB real, produccion, SII real, EDIG ejecutable ni integraciones externas sin autorizacion explicita. Las salidas F22/DDJJ/Balance/RLI/CPT/RAI/SAC esperadas son comparacion externa read-only, nunca input de calculo. |
| Siguiente accion | Completar validacion impactada, PR/CI/merge y limpiar `stage6-value-error-filter`; luego continuar con el siguiente blocker concreto de la prueba espejo. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
