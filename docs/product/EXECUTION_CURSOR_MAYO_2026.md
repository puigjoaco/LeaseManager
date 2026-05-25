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
| Frente activo | Ninguno. Ultimo paquete cerrado: Etapa 1 - Patrimonio, duplicidad de participantes actualmente vigentes. |
| Fuente exacta | PR #223 `Guard Stage 1 participant duplicate window`; commit `6201f5a`; merge `170d440`; `backend/patrimonio/models.py`; `backend/patrimonio/serializers.py`; `backend/core/stage1_matrix_audit.py`; `backend/patrimonio/tests.py`; `backend/core/tests_stage1_matrix_audit.py`; stage card, trazabilidad y evidencia actualizadas. |
| Brecha activa | Cerrada localmente: duplicados de participantes se evaluan sobre la ventana actualmente vigente, se permite historial no vigente del mismo participante y dominio/auditor bloquean duplicados vigentes en empresa/comunidad activa. |
| Motivo de prioridad | Paquete local, pequeno y verificable completado sin secretos, `.env`, DB historica, datos reales ni integraciones externas. |
| Worktree | Ninguno. Solo debe quedar el worktree principal `D:/Proyectos/LeaseManager`. |
| Rama | `main`, sincronizada con `origin/main`. |
| Estado | PR #223 integrado con CI remoto verde; worktree tactico y ramas local/remota eliminados. |
| Gate esperado | Etapa 1 local queda como diagnostico parcial/no evidencial; no cierra Etapa 1 sin `snapshot_controlado` o `real_autorizado`. |
| Estado al cerrar paquete | Preparacion local de Patrimonio reforzada; cierre real de Etapa 1 sigue pendiente de fuente autorizada y evidencia suficiente. |
| Bloqueos relacionados | Cierres que requieran fuente autorizada/evidencia externa quedan como condicion de cierre; no bloquean tomar el siguiente frente seguro. |
| Politica de reanudacion | Si `main` esta limpio y no hay worktrees tacticos sucios, diagnosticar el siguiente paquete pequeno, trazable y local desde la matriz/stage cards. |
| Siguiente accion | Confirmar `git status --short --branch` y `git worktree list`; elegir el siguiente frente seguro por trazabilidad y abrir worktree `codex/...` solo si requiere cambios no triviales. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
