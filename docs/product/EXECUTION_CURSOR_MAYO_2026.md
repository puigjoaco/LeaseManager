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
| Frente activo | Etapa 1 / Contratos - redaccion admin de refs de arrendatario y contacto de pago. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | `ArrendatarioAdmin` y `ContactoPagoArrendatarioAdmin` aun pueden exponer refs/motivos sensibles heredados mediante campos crudos por defecto del admin Django. |
| Motivo de prioridad | Primer frente local seguro en Contratos tras confirmar `main` limpio y sin paquete activo; no requiere secretos, `.env`, datos reales ni integraciones. |
| Worktree | `D:/Proyectos/LeaseManager-stage1-contract-tenant-admin-redaction`. |
| Rama | `codex/stage1-contract-tenant-admin-redaction`. |
| Estado | Abierto para cerrar superficie admin de refs WhatsApp/contactos de pago con tests y evidencia. |
| Gate esperado | Tests focales de admin Contratos, suite impactada Contratos/Etapa 1, `manage.py check`, `makemigrations --check --dry-run`, readiness local Etapa 1, frontend build/lint, acceptance local, higiene repo y CI remoto. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Sin bloqueo externo nuevo. |
| Politica de reanudacion | Continuar este worktree hasta PR/CI/merge o pausar explicitamente aqui si aparece un bloqueo real. |
| Siguiente accion | Implementar redaccion admin, cubrir con tests, actualizar stage card/trazabilidad/evidencia y cerrar paquete. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
