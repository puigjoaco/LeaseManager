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
| Frente activo | Compliance / exportaciones sensibles. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | La revocacion de `ExportacionSensible` queda auditada, pero no exige motivo no sensible ni readiness bloqueante para eventos `revoked` heredados sin motivo. |
| Motivo de prioridad | Frente temprano local: fortalece auditoria de acciones criticas sobre datos personales sin requerir `.env`, secretos, datos reales ni integraciones externas. |
| Worktree | `D:/Proyectos/LeaseManager-compliance-export-revoke-reason`. |
| Rama | `codex/compliance-export-revoke-reason`. |
| Estado | Paquete abierto para exigir motivo de revocacion no sensible en API, auditoria y readiness. |
| Gate esperado | Focal Compliance/readiness; suite `compliance core.tests_compliance_data_readiness`; `manage.py check`; `makemigrations --check --dry-run`; frontend build; acceptance; higiene repo. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Sin bloqueo externo nuevo. |
| Politica de reanudacion | Si no existe worktree tactico sucio, tomar el siguiente frente seguro desde trazabilidad y abrirlo explicitamente en este cursor. |
| Siguiente accion | Implementar y validar motivo auditable no sensible para revocacion de exportaciones sensibles. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
