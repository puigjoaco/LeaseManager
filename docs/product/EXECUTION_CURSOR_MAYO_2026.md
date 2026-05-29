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
| Frente activo | Sin paquete tactico abierto posterior a integrar este paquete. |
| Fuente exacta | Estado real de `main` base `2f13492`, PRD canonico, `docs/product/TRACEABILITY_MATRIX_MAYO_2026.md`, stage cards, evidencia y bloqueos vigentes. |
| Brecha activa | Cerrada por este paquete: `formalizar/` guardaba el cambio de estado antes de crear auditoria, permitiendo una formalizacion parcial si fallaba la escritura del evento. |
| Motivo de prioridad | La formalizacion documental es un acto auditado; el estado `formalizado` no debe persistir si no queda tambien el evento dedicado y trazable. |
| Worktree | Ninguno tras merge. Durante la ejecucion se uso `D:/Proyectos/LeaseManager-stage5-formalization-atomic-audit`. |
| Rama | `main` tras merge; laboratorio usado: `codex/stage5-formalization-atomic-audit`. |
| Estado | Paquete Etapa 5 / Documentos / atomicidad de formalizacion y auditoria preparado para integracion: implementacion, pruebas locales y gates proporcionales OK. |
| Gate esperado | Focal Documentos, suite `documentos`, `manage.py check`, `makemigrations --check --dry-run`, gate local Etapa 5 Documentos, acceptance local, higiene repo y `git diff --check`. |
| Estado al cerrar paquete | Etapa 5 / Documentos / atomicidad de formalizacion y auditoria: validacion local OK con focal 2 tests, suite `documentos` 83 tests, `manage.py check`, migraciones dry-run, gate local Etapa 5 Documentos parcial esperado, `npm ci` 0 vulnerabilidades, `npm run build`, acceptance 1100 tests, higiene repo y `git diff --check`. |
| Bloqueos relacionados | Sin bloqueo externo nuevo; Documentos/Etapa 5 no se declara cerrado sin fuente `snapshot_controlado` o `real_autorizado`, politica final, plantillas activas finales, prueba PDF controlada y responsable. |
| Politica de reanudacion | Si `git status` y `git worktree list` muestran solo `main` limpio, diagnosticar el siguiente frente seguro; si aparece un worktree sucio, terminar o pausar ese paquete antes de abrir otro frente. |
| Siguiente accion | Diagnosticar el siguiente frente seguro desde el estado real del repo. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
