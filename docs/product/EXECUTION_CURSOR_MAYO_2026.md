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
| Frente activo | PlataformaBase / Auditoria admin redaction. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | `backend/audit/admin.py` registra `AuditEvent` y `ManualResolution` con admin crudo, exponiendo metadata/rationale/resumen sensible heredado por fuera de serializers. |
| Motivo de prioridad | Cierra superficie transversal de auditoria, consistente con el hardening admin reciente de dominios y Compliance. |
| Worktree | `D:/Proyectos/LeaseManager-audit-admin-redaction`. |
| Rama | `codex/audit-admin-redaction`. |
| Estado | Implementado y validado localmente; pendiente commit, PR, CI, merge y limpieza. |
| Gate esperado | Tests focales de auditoria admin, suite `audit`, `manage.py check`, migraciones dry-run, acceptance local, build frontend e higiene. |
| Estado al cerrar paquete | Admin de auditoria explicito implementado; `AuditEvent` y `ManualResolution` no exponen campos crudos sensibles en Django admin, no permiten alta/borrado manual y quedaron cubiertos por pruebas/evidencia local. |
| Bloqueos relacionados | Sin bloqueo externo nuevo. |
| Politica de reanudacion | Continuar este worktree hasta PR/CI/merge/limpieza antes de abrir otro paquete. |
| Siguiente accion | Crear commit, abrir PR, esperar CI, mergear y limpiar worktree. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
