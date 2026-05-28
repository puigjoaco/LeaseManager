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
| Frente activo | Etapa 0 - PlataformaBase/Auth. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | Auth expone `User.metadata` sin redaccion defensiva en `CurrentUserSerializer`; login demo devuelve una `signature` interna derivada de metadata cruda. |
| Motivo de prioridad | Superficie base temprana: metadata de usuario puede contener referencias operativas y debe seguir el mismo criterio de redaccion defensiva aplicado a auditoria/admin. |
| Worktree | `D:/Proyectos/LeaseManager-platform-user-metadata-redaction`. |
| Rama | `codex/platform-user-metadata-redaction`. |
| Estado | En desarrollo. |
| Gate esperado | Acceptance local y CI remoto deben permanecer verdes; no requiere fuentes externas. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Sin bloqueo externo nuevo. |
| Politica de reanudacion | Continuar solo este worktree hasta PR/CI/merge/limpieza o pausar aqui con estado explicito. |
| Siguiente accion | Redactar metadata de usuario expuesta, ocultar signature interna y validar con pruebas de Auth. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
