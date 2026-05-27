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
| Frente activo | Sin paquete activo. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | Ninguna abierta. |
| Motivo de prioridad | Paquete cerrado: Reporting completa las metricas PRD del dashboard operativo. |
| Worktree | N/A tras merge y limpieza. |
| Rama | N/A tras merge y limpieza. |
| Estado | Paquete validado y listo para quedar integrado: `build_operational_dashboard` expone los contadores PRD desde el payload base usado por Overview y el backoffice muestra los bloqueadores operativos sin depender de fuentes externas. |
| Gate esperado | N/A hasta abrir proximo paquete. |
| Estado al cerrar paquete | Validaciones locales completas: focal 1 test, suite Reporting 25 tests, suite impactada Reporting/permisos/scope 43 tests, `manage.py check`, `makemigrations --check --dry-run`, gate Etapa 7 local parcial esperado, `npm ci`, `npm run build`, `npm run lint`, acceptance 951 tests, higiene y `git diff --check`. |
| Bloqueos relacionados | Sin bloqueo externo nuevo. |
| Politica de reanudacion | Si no existe worktree tactico sucio, tomar el siguiente frente seguro desde trazabilidad y abrirlo explicitamente en este cursor. |
| Siguiente accion | Tras merge y limpieza, diagnosticar estado real y seleccionar siguiente paquete pequeno, local y verificable por trazabilidad. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
