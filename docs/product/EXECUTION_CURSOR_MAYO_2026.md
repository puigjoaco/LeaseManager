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
| Frente activo | `stage6-value-token-union`. |
| Fuente exacta | worktree `D:/Proyectos/10_ACTIVOS/LeaseManager-stage6-value-token-union`, creado sobre `main` `76dc785e`. |
| Brecha activa | El comparador de valores AC2024/AT2025 extrae muchos archivos para `balance_general`, pero usaba solo el ultimo set de tokens por `category/artifact_key`, dejando 136 falsos faltantes en Balance. |
| Motivo de prioridad | La prueba espejo debe probar si LeaseManager llega a los outputs finales desde inputs 2024. Si el comparador sobrescribe paginas/archivos de Balance, la arquitectura parece incompleta aunque las senales esperadas ya existan en otros archivos. |
| Worktree | Continuar/cerrar `D:/Proyectos/10_ACTIVOS/LeaseManager-stage6-value-token-union`. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `codex/stage6-value-token-union`; al cerrar, PR/CI/merge y limpiar worktree. |
| Estado | En desarrollo validado focalmente: `extract_expected_output_value_signals` une tokens por `category/artifact_key`. Contraste local AC2024/AT2025: Balance usa 1046 tokens esperados, `Compared=138`, `Matched=138`, `Missing=0`, `BlockingExtractionErrors=0`; el mirror proof conserva blockers reales de Stage 6. |
| Gate esperado | El comparador queda sin blockers, pero Etapa 6/mirror proof sigue `classification=parcial` si persisten `stage6.enterprise_register_movement_invalid` y `stage6.real_estate_item_missing`. No usa outputs finales como input, no abre SII real, no declara cierre tributario final ni presentacion SII. |
| Estado al cerrar paquete | No reabrir Compliance #879, filtro de errores #880, paquetes Stage 6 ya mergeados ni prompts de goal. El siguiente frente real debe tomar registros empresariales invalidos o bienes raices faltantes segun mirror proof. |
| Bloqueos relacionados | Tras este paquete, los blockers de comparacion de valores deben desaparecer. La prueba espejo total sigue pendiente por `stage6.enterprise_register_movement_invalid` y `stage6.real_estate_item_missing`. |
| Politica de reanudacion | No usar `.env`, secretos, DB real, produccion, SII real, EDIG ejecutable ni integraciones externas sin autorizacion explicita. Las salidas F22/DDJJ/Balance/RLI/CPT/RAI/SAC esperadas son comparacion externa read-only, nunca input de calculo. |
| Siguiente accion | Completar validacion impactada, PR/CI/merge y limpiar `stage6-value-token-union`; luego continuar con `stage6.enterprise_register_movement_invalid` o `stage6.real_estate_item_missing`. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
