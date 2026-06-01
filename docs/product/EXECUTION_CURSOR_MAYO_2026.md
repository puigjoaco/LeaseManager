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
| Frente activo | Documentos - atomicidad de updates genericos y auditoria de vista. |
| Fuente exacta | Estado real de `main` en `9186bed` despues de PR #621, stage cards, trazabilidad, evidencia y bloqueos vigentes. |
| Brecha activa | `backend/documentos/views.py` guarda updates genericos dentro de transaccion pero registra `updated` y `state_changed` fuera de ella. Si falla esa auditoria, puede quedar una politica, expediente, plantilla o documento mutado sin traza de endpoint. |
| Motivo de prioridad | La brecha es local, verificable, afecta el gate documental y no depende de datos reales, DB historicas, snapshots autorizados, backfills, deploys ni integraciones externas. |
| Worktree | `D:/Proyectos/LeaseManager-documents-update-audit-atomicity`. |
| Rama | `codex/documents-update-audit-atomicity`. |
| Estado | Paquete tactico abierto. |
| Gate esperado | Tests focales de rollback ante falla de auditoria, suite impactada Documentos/readiness, `manage.py check`, migraciones dry-run, frontend build/lint, acceptance local, higiene y CI GitHub. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | No hay bloqueo externo para este paquete local. No usa `.env`, secretos, DB historicas, datos reales, snapshots autorizados, backfills, deploys ni integraciones externas. |
| Politica de reanudacion | Si este worktree aparece sucio, terminar o pausar este paquete antes de abrir otro frente. Si no existe, confirmar el cursor actualizado en `main` antes de diagnosticar el siguiente frente. |
| Siguiente accion | Implementar atomicidad, pruebas focales, documentacion/evidencia, validaciones proporcionales, PR, CI, merge y limpieza. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
