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
| Fuente exacta | Estado real de `main` base `fc808d6`, PRD canonico, `docs/product/TRACEABILITY_MATRIX_MAYO_2026.md`, stage cards, evidencia y bloqueos vigentes. |
| Brecha activa | Cerrada por este paquete: `prepare_message()` persistia mensajes preparados o bloqueados, pero el evento `canales.mensaje_saliente.prepared` quedaba en la vista HTTP. Las llamadas internas no quedaban auditadas y una falla posterior de auditoria podia dejar mensaje sin evento de preparacion. |
| Motivo de prioridad | La preparacion de mensajes es una operacion critica de Canales: estado del mensaje, gate, identidad y contexto deben quedar persistidos junto con auditoria trazable dentro de la misma transaccion. |
| Worktree | Ninguno tras merge. Durante la ejecucion se uso `D:/Proyectos/LeaseManager-stage2-message-prepare-audit`. |
| Rama | `main` tras merge; laboratorio usado: `codex/stage2-message-prepare-audit`. |
| Estado | Paquete Etapa 2 / Canales / auditoria atomica de preparacion de mensajes preparado para integracion: implementacion, pruebas locales y gates proporcionales OK. |
| Gate esperado | Focal Canales, suite `canales` y readiness Etapa 2, `manage.py check`, `makemigrations --check --dry-run`, gate local Etapa 2, acceptance local, higiene repo y `git diff --check`. |
| Estado al cerrar paquete | Etapa 2 / Canales / auditoria atomica de preparacion de mensajes: validacion local OK con focal 3 tests, suite `canales` + readiness Etapa 2 140 tests, `manage.py check`, migraciones dry-run, gate local Etapa 2 parcial esperado, `npm ci` 0 vulnerabilidades, `npm run build`, `npm run lint`, acceptance 1102 tests, higiene repo y `git diff --check`. |
| Bloqueos relacionados | Sin bloqueo externo nuevo; Etapa 2/Canales no se declara cerrada sin fuente `snapshot_controlado` o `real_autorizado`, evidencia Etapa 1, prueba Email/WebPay controlada y responsables. |
| Politica de reanudacion | Si `git status` y `git worktree list` muestran solo `main` limpio, diagnosticar el siguiente frente seguro; si aparece un worktree sucio, terminar o pausar ese paquete antes de abrir otro frente. |
| Siguiente accion | Diagnosticar el siguiente frente seguro desde el estado real del repo. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
