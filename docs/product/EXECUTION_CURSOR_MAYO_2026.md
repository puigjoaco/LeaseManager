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
| Frente activo | Etapa 3 - atomicidad del reintento manual de match exacto. |
| Fuente exacta | Estado real de `main` en `e87c81b` despues de PR #613, stage cards, trazabilidad, evidencia y bloqueos vigentes. |
| Brecha activa | `backend/conciliacion/views.py::MovimientoBancarioRetryMatchView` ejecuta `reconcile_exact_movement()` antes de registrar `conciliacion.movimiento_bancario.match_retried`. Si falla esa auditoria de vista, podrian quedar pago, ingreso desconocido, supersesion o movimiento mutados sin traza del reintento manual. |
| Motivo de prioridad | Conciliacion es el siguiente frente del orden de construccion despues de CobranzaActiva, y la brecha es local, verificable y no depende de banco real ni snapshot autorizado. |
| Worktree | `D:/Proyectos/LeaseManager-stage3-retry-match-audit-atomicity`. |
| Rama | `codex/stage3-retry-match-audit-atomicity`. |
| Estado | Paquete tactico abierto. |
| Gate esperado | Test focal de rollback de reintento, suite impactada Conciliacion/Etapa 3, `manage.py check`, migraciones dry-run, gate local Etapa 3 diagnostico, frontend build/lint, acceptance local, higiene y CI GitHub. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | El cierre evidencial de Etapa 3 sigue condicionado por fuente `snapshot_controlado` o `real_autorizado`, prueba bancaria y cuadratura autorizada. Este paquete local no usa `.env`, secretos, DB historicas, datos reales, banco real, snapshots autorizados, backfills, deploys ni integraciones externas. |
| Politica de reanudacion | Si este worktree aparece sucio, terminar o pausar este paquete antes de abrir otro frente. Si no existe, confirmar el cursor actualizado en `main` antes de diagnosticar el siguiente frente. |
| Siguiente accion | Completar implementacion, pruebas focales, documentacion/evidencia, validaciones proporcionales, PR, CI, merge y limpieza. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
