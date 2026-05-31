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
| Frente activo | Ningun paquete tactico abierto. |
| Fuente exacta | Estado real de `main` en `ac716fa` despues de PR #608, stage cards, trazabilidad, evidencia y bloqueos vigentes. |
| Brecha activa | Ninguna seleccionada en este cursor. |
| Motivo de prioridad | PR #608 cerro la atomicidad de auditoria en APIs de Operacion; el siguiente frente debe diagnosticarse desde `main` limpio y la trazabilidad vigente. |
| Worktree | Ninguno. |
| Rama | `main`. |
| Estado | Listo para diagnosticar el siguiente frente seguro. |
| Gate esperado | No aplica hasta abrir un nuevo paquete. |
| Estado al cerrar paquete | PR #608 mergeado en `ac716fa`: `backend/operacion/views.py::AuditCreateUpdateMixin` persiste altas/ediciones operativas y eventos `created`, `updated` o `state_changed` en una sola transaccion. Si falla la auditoria, no quedan cuentas recaudadoras, identidades, mandatos ni asignaciones de canal mutadas sin traza. Validado con focal 4 tests, impactada Operacion/Etapa 1 174 tests, `manage.py check`, `makemigrations --check --dry-run --noinput`, readiness local Etapa 1 no evidencial, `npm ci`, `npm run build`, `npm run lint`, acceptance local 1141 tests, higiene, `git diff --check` y CI GitHub. |
| Bloqueos relacionados | BLK-002 sigue abierto para cierre evidencial de Etapa 1 con fuente `snapshot_controlado` o `real_autorizado`. El paquete cerrado no uso `.env`, secretos, DB historica, datos reales, snapshots autorizados, backfills, deploys ni integraciones externas. |
| Politica de reanudacion | Si `git status` y `git worktree list` muestran solo `main` limpio, diagnosticar el siguiente frente seguro; si aparece un worktree sucio, terminar o pausar ese paquete antes de abrir otro frente. |
| Siguiente accion | Confirmar `main` limpio y diagnosticar el siguiente frente seguro por orden de construccion y trazabilidad vigente. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
