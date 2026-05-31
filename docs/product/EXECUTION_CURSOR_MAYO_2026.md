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
| Frente activo | Etapa 3 - atomicidad de auditoria en creacion de movimiento bancario y match de conciliacion. |
| Fuente exacta | Estado real de `main` en `91dc7b2` despues de PR #603, stage cards, trazabilidad, evidencia y bloqueos vigentes. |
| Brecha activa | `MovimientoBancarioListCreateView.perform_create` no mantiene en una unica transaccion la persistencia del movimiento, la auditoria `created`, el match local y la auditoria `match_attempted`; si falla la auditoria posterior, pueden quedar efectos de conciliacion sin traza completa. |
| Motivo de prioridad | Etapa 3 exige que importaciones, matches y resoluciones pasen por APIs/servicios auditados; la correccion es local, verificable y no requiere banco real, snapshot, secretos ni integraciones externas. |
| Worktree | `D:/Proyectos/LeaseManager-stage3-movement-audit-atomicity`. |
| Rama | `codex/stage3-movement-audit-atomicity`. |
| Estado | Paquete tactico abierto. |
| Gate esperado | Etapa 3 local debe seguir `classification=parcial`, `ready_for_stage3_conciliacion=false`, sin cierre evidencial. |
| Estado al cerrar paquete | PR #602 mergeado en `8651741`: `ExportacionContentView` ejecuta descarga/denegacion y eventos `accessed`/`access_denied` dentro de una transaccion. Si falla la auditoria de acceso denegado, la normalizacion de exportacion vencida a `expirada` se revierte. Validado con focal 3 tests, impactada Compliance/readiness 101 tests, `manage.py check`, `makemigrations --check --dry-run --noinput`, gate Compliance parcial esperado, `npm ci`, `npm run build`, `npm run lint`, acceptance local 1135 tests, higiene, `git diff --check` y CI GitHub. |
| Bloqueos relacionados | BLK-010 sigue abierto para cierre legal-operativo y fuente autorizada. El paquete cerrado no uso `.env`, secretos, DB historica, datos reales, snapshots autorizados, backfills, deploys ni integraciones externas. |
| Politica de reanudacion | Si `git status` y `git worktree list` muestran solo `main` limpio, diagnosticar el siguiente frente seguro; si aparece un worktree sucio, terminar o pausar ese paquete antes de abrir otro frente. |
| Siguiente accion | Implementar transaccion atomica para creacion/match de movimiento bancario, agregar prueba de rollback ante fallo de auditoria, validar suite impactada y cerrar con PR/CI/merge/limpieza. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
