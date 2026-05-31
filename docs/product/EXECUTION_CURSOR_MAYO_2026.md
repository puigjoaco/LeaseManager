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
| Frente activo | Etapa 1 - atomicidad de auditoria en APIs de Patrimonio. |
| Fuente exacta | Estado real de `main` en `fa5e091` despues de PR #605, stage cards, trazabilidad, evidencia y bloqueos vigentes. |
| Brecha activa | `backend/patrimonio/views.py::AuditCreateUpdateMixin` persiste altas/ediciones patrimoniales antes de crear auditoria y fuera de una transaccion unica; si falla `create_audit_event`, pueden quedar cambios patrimoniales sin traza. |
| Motivo de prioridad | Patrimonio es el primer dominio de construccion despues de PlataformaBase; la correccion es local, verificable y no requiere datos reales, snapshot, secretos ni integraciones externas. |
| Worktree | `D:/Proyectos/LeaseManager-stage1-patrimony-audit-atomicity`. |
| Rama | `codex/stage1-patrimony-audit-atomicity`. |
| Estado | Paquete tactico abierto. |
| Gate esperado | Etapa 1 local debe seguir como diagnostico no evidencial, sin cierre de etapa por falta de fuente autorizada. |
| Estado al cerrar paquete | PR #604 mergeado en `4b65376`: `AuditCreateUpdateMixin` persiste creacion/actualizacion y auditoria en una sola transaccion, y `MovimientoBancarioListCreateView.perform_create()` persiste movimiento, auditoria `created`, match exacto local y auditoria `match_attempted` de forma atomica. Si falla la auditoria posterior, no quedan movimiento, pago mutado, ingreso desconocido ni estado de conciliacion sin traza. Validado con focal 3 tests, impactada Conciliacion/readiness 112 tests, `manage.py check`, `makemigrations --check --dry-run --noinput`, gate Etapa 3 parcial esperado, `npm ci`, `npm run build`, `npm run lint`, acceptance local 1137 tests, higiene, `git diff --check` y CI GitHub. |
| Bloqueos relacionados | Etapa 3 sigue parcial para cierre real porque requiere banco real o snapshot autorizado, evidencia Etapa 2, prueba bancaria y cuadratura controlada. El paquete cerrado no uso `.env`, secretos, DB historica, datos reales, snapshots autorizados, backfills, deploys ni integraciones externas. |
| Politica de reanudacion | Si `git status` y `git worktree list` muestran solo `main` limpio, diagnosticar el siguiente frente seguro; si aparece un worktree sucio, terminar o pausar ese paquete antes de abrir otro frente. |
| Siguiente accion | Implementar transaccion atomica en APIs de Patrimonio, agregar pruebas de rollback ante fallo de auditoria, validar suite impactada y cerrar con PR/CI/merge/limpieza. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
