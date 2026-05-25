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
| Frente activo | Ninguno. Ultimo paquete cerrado: Etapa 1 - Patrimonio, ventana efectiva de representaciones de comunidad. |
| Fuente exacta | PR #221 (`Guard Stage 1 community representation window`), commit `ea548aa`, merge `0dd724e`; `backend/patrimonio/models.py`; `backend/patrimonio/serializers.py`; `backend/patrimonio/views.py`; `backend/patrimonio/tests.py`; `backend/core/tests_stage1_matrix_audit.py`; stage card, trazabilidad y evidencia Etapa 1. |
| Brecha activa | Cerrada localmente: las representaciones de comunidad solo cuentan como vigentes si `activo=True`, `vigente_desde` ya fue alcanzado y `vigente_hasta` no vencio. |
| Motivo de prioridad | Paquete seguro completado sin secretos, `.env`, datos reales, snapshots, backfills, deploys ni integraciones externas. |
| Worktree | Ninguno. Solo debe quedar el worktree principal `D:/Proyectos/LeaseManager`. |
| Rama | `main` sincronizada con `origin/main`. |
| Estado | PR #221 integrado con CI `acceptance` verde; worktree tactico y rama local/remota eliminados. |
| Gate esperado | Etapa 1 local sigue como diagnostico no evidencial; no cierra Etapa 1 sin `snapshot_controlado` o `real_autorizado`. |
| Estado al cerrar paquete | Preparacion local de Patrimonio reforzada; cierre real de Etapa 1 sigue pendiente por fuente/evidencia autorizada. |
| Bloqueos relacionados | Cierre real de Etapa 1 requiere fuente autorizada y evidencia suficiente; no bloquea preparacion local ni el siguiente frente seguro. |
| Politica de reanudacion | Si `main` esta limpio y no hay worktrees tacticos sucios, diagnosticar el siguiente frente seguro segun trazabilidad y orden de construccion. |
| Siguiente accion | Confirmar `git status --short --branch` y `git worktree list`; elegir el siguiente paquete pequeno, seguro y verificable desde trazabilidad/stage cards. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
