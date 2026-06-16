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
| Frente activo | `stage6-enterprise-movement-hash`. |
| Fuente exacta | worktree `D:/Proyectos/10_ACTIVOS/LeaseManager-stage6-enterprise-movement-hash`, creado sobre `main` `ed3b1e16`. |
| Brecha activa | La prueba espejo AC2024/AT2025 ya tiene comparador verde, pero readiness Etapa 6 reporta 7 movimientos de registros empresariales invalidos porque `hash_movimiento` se calculaba antes de normalizar el movimiento persistido. |
| Motivo de prioridad | Es una brecha de integridad generada por LeaseManager, no una falta de permiso externo. Mientras los hashes de RAI/SAC no coincidan con el payload canonico, la arquitectura anual parece no cerrable aunque los registros existan. |
| Worktree | Continuar/cerrar `D:/Proyectos/10_ACTIVOS/LeaseManager-stage6-enterprise-movement-hash`. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `codex/stage6-enterprise-movement-hash`; al cerrar, PR/CI/merge y limpiar worktree. |
| Estado | En desarrollo validado focalmente: `_save_enterprise_movement` normaliza `monto_clp` y recalcula `hash_movimiento` desde la instancia. En copia controlada AC2024/AT2025, movimientos empresariales quedan `invalid_total=0`; readiness baja a un solo blocker: `stage6.real_estate_item_missing`. |
| Gate esperado | Etapa 6/mirror proof sigue `classification=parcial` porque falta materializar bienes raices/contribuciones, pero ya no debe reportar `stage6.enterprise_register_movement_invalid`. No usa outputs finales como input, no abre SII real, no declara cierre tributario final ni presentacion SII. |
| Estado al cerrar paquete | No reabrir Compliance #879, filtro #880, union de tokens #881, paquetes Stage 6 ya mergeados ni prompts de goal. El siguiente frente real debe tomar `stage6.real_estate_item_missing`. |
| Bloqueos relacionados | Tras este paquete, la prueba espejo total queda pendiente por bienes raices faltantes y los blockers agregados que dependen de esa arquitectura/fuente. |
| Politica de reanudacion | No usar `.env`, secretos, DB real, produccion, SII real, EDIG ejecutable ni integraciones externas sin autorizacion explicita. Las salidas F22/DDJJ/Balance/RLI/CPT/RAI/SAC esperadas son comparacion externa read-only, nunca input de calculo. |
| Siguiente accion | Completar validacion, PR/CI/merge y limpiar `stage6-enterprise-movement-hash`; luego continuar con `stage6.real_estate_item_missing`. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
