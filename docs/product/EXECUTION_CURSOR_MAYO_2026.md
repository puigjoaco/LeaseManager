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
| Frente activo | Ninguno. Ultimo paquete cerrado: Etapa 1 - Contratos, decision auditada para prorrata por terminacion anticipada. |
| Fuente exacta | PR #253, commit `91e8afa`, merge `e58692a`; PRD `01_Set_Vigente/PRD_CANONICO.md` lineas 342-345; `backend/contratos/models.py`; `backend/contratos/serializers.py`; `backend/contratos/views.py`; `backend/core/stage1_matrix_audit.py`; `frontend/src/backoffice/workspaces/ContratosWorkspace.tsx`; stage card, trazabilidad y evidencia. |
| Brecha activa | Cerrada localmente: ultimo mes parcial en terminacion anticipada exige regla o decision de prorrata no sensible, motivo trazable y evento auditable dedicado; auditor Etapa 1 bloquea snapshots heredados sin decision o sin auditoria. |
| Motivo de prioridad | Paquete de Contratos derivado del PRD, cerrado con validacion local, CI y merge sin `.env`, secretos, DB historica, datos reales ni integraciones externas. |
| Worktree | Ninguno. Solo debe quedar el worktree principal. |
| Rama | `main` sincronizada con `origin/main` despues de PR #254. |
| Estado | Listo para reanudacion operativa desde el siguiente paquete de producto seguro. |
| Gate esperado | Etapa 1 local queda como diagnostico no evidencial; no cierra sin fuente `snapshot_controlado` o `real_autorizado`. |
| Estado al cerrar paquete | Validado, PR #253 mergeado con CI acceptance verde, cursor cerrado en PR #254 y worktrees tacticos eliminados. |
| Bloqueos relacionados | Fuente autorizada de Etapa 1 y evidencia externa/controlada siguen siendo condicion de cierre real de etapa, no de avance local seguro. |
| Politica de reanudacion | Confirmar estado real con `git status --short --branch` y `git worktree list`; si no hay worktree tactico abierto, elegir el siguiente paquete seguro por trazabilidad. |
| Siguiente accion | Seleccionar el siguiente paquete seguro desde stage cards, trazabilidad y PRD; abrir worktree `codex/...` si el cambio no es trivial. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
