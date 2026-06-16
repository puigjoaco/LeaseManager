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
| Frente activo | `main-clean-next-traceable-front`. |
| Fuente exacta | `main` posterior al cierre del gate espejo backend y del wrapper operativo Stage 6 mirror proof. |
| Brecha activa | No hay paquete tactico abierto para AC2024/AT2025. El comando Django y el wrapper operativo del gate espejo quedan como camino canonico para futuras corridas controladas o autorizadas. |
| Motivo de prioridad | Evitar reabrir paquetes cerrados y mantener la siguiente decision basada en el estado real del repo, trazabilidad y cursor. |
| Worktree | Ningun worktree tactico de AC2024/AT2025 debe quedar activo despues de mergear el wrapper. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `main` limpio despues de cerrar el wrapper. Para el proximo paquete no trivial abrir worktree hermano `codex/...` desde `main`. |
| Estado | El gate espejo AC2024/AT2025 distingue fuente documentada, arquitectura espejo, comparacion lista, readiness Etapa 6, seguridad y revision pendiente. El wrapper `scripts/run-stage6-mirror-proof-gate.ps1` valida refs no sensibles, salida bajo `local-evidence/`, manifiestos/source-root no versionables y bloqueo de migraciones con `real_autorizado`. |
| Gate esperado | Para AC2024/AT2025 controlado o autorizado, usar `scripts/run-stage6-mirror-proof-gate.ps1`; con `-FailOnIncomplete` solo si se exige `ready_for_objective_completion=true`. Para otros frentes, elegir el siguiente paquete trazable desde `main` limpio. |
| Estado al cerrar paquete | No reabrir prompts de goal, boundary contable de PR #859, gate espejo backend, wrapper Stage 6, selector anual, ownership, respaldo tributario, bienes raices, DDJJ/F22 semantico, Balance General, RLI/CPT/RAI/SAC ni EDIG como bloqueo general salvo bug nuevo. |
| Bloqueos relacionados | Sin autorizacion o fuente real no se debe presentar SII, declarar calculo tributario final ni afirmar cierre productivo. El bloqueo externo queda como condicion de cierre real/productivo, no como freno para seguir por el siguiente frente seguro. |
| Politica de reanudacion | No reabrir goal prompts, EDIG ni paquetes mergeados. No usar `.env`, secretos, DB real, produccion, SII real ni integraciones externas sin autorizacion explicita. Si falta fuente externa, continuar con preparacion local segura y trazable. |
| Siguiente accion | Continuar el siguiente frente trazable desbloqueado desde `main` limpio, o correr el gate espejo solo si existe fuente controlada/autorizada y refs no sensibles suficientes. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
