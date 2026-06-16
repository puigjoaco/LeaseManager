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
| Frente activo | `stage6-mirror-proof-wrapper`. |
| Fuente exacta | `main` posterior al merge de PR #860 (`5fecfd2f`) y PR #859 (`2883fa65`). |
| Brecha activa | Existe worktree tactico sucio con un wrapper Stage 6 mirror proof pendiente de revisar/cerrar. No abrir otro frente hasta terminarlo, pausarlo explicitamente o descartarlo con instruccion segura. |
| Motivo de prioridad | Evitar perder o pisar cambios locales existentes y mantener una sola continuacion objetiva tras PR #860/#861. |
| Worktree | `D:/Proyectos/10_ACTIVOS/LeaseManager-stage6-mirror-proof-wrapper` en rama `codex/stage6-mirror-proof-wrapper`, con cambios locales en cursor, stage card, trazabilidad, `scripts/run-acceptance-workflows.ps1` y `scripts/run-stage6-mirror-proof-gate.ps1`. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `codex/stage6-mirror-proof-wrapper` en el worktree tactico indicado. `main` queda limpio despues de PR #861. |
| Estado | PR #860 cerro el gate espejo AC2024/AT2025 en backend/CLI/docs y PR #861 cerro el cursor post-merge. Queda pendiente inspeccionar el worktree `stage6-mirror-proof-wrapper` para decidir si sus cambios complementan el gate como wrapper operativo o si deben pausarse/descartarse. |
| Gate esperado | Primero ejecutar `git status --short --branch` y revisar el diff del worktree `stage6-mirror-proof-wrapper`. Si se conserva, validar proporcionalmente el wrapper Stage 6 y cerrar con PR/CI/merge; si no corresponde, pausarlo en cursor o descartarlo solo con instruccion segura. |
| Estado al cerrar paquete | No reabrir prompts de goal, boundary contable de PR #859, selector anual, ownership, respaldo tributario, bienes raices, DDJJ/F22 semantico, Balance General, RLI/CPT/RAI/SAC ni EDIG como bloqueo general salvo bug nuevo. El gate espejo queda como punto unico para decir preparado, parcial o bloqueado. |
| Bloqueos relacionados | Sin autorizacion o fuente real no se debe presentar SII, declarar calculo tributario final ni afirmar cierre productivo. El bloqueo externo queda como condicion de cierre real/productivo, no como freno para seguir por el siguiente frente seguro. |
| Politica de reanudacion | No reabrir goal prompts, EDIG ni paquetes mergeados. No usar `.env`, secretos, DB real, produccion, SII real ni integraciones externas sin autorizacion explicita. Si falta fuente externa, continuar con preparacion local segura y trazable. |
| Siguiente accion | Continuar o cerrar `D:/Proyectos/10_ACTIVOS/LeaseManager-stage6-mirror-proof-wrapper` antes de abrir otro frente. No reabrir prompts de goal ni paquetes AC2024 ya mergeados salvo bug nuevo. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
