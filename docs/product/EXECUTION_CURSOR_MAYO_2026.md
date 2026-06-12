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
| Frente activo | Sin paquete tactico abierto tras cerrar normalizacion de metadata visible operacional. |
| Fuente exacta | `main` limpio tras mergear este paquete; PR #765 (`73872ab8`) fue la base anterior y rescue queda pausado fuera de alcance. |
| Brecha activa | Ninguna brecha activa debe reabrirse desde este cursor tras mergear el paquete. La brecha de metadata visible operacional queda cubierta por modelo, auditor Etapa 1, stage card, trazabilidad y evidencia. |
| Motivo de prioridad | Evitar que reanudaciones o compactaciones reabran el paquete de Operacion ya validado. |
| Worktree | Ninguno tras merge y limpieza del paquete. |
| Rama | `main` tras merge. |
| Estado | Listo para seleccionar el siguiente frente util y seguro desde el repo limpio despues de PR/CI/merge/limpieza. |
| Gate esperado | El siguiente paquete debe definir su gate proporcional antes de editar; los cierres evidenciales siguen sin declararse sin fuente autorizada y evidencia. |
| Estado al cerrar paquete | Operacion metadata visible: focal 4 tests OK; suite impactada Operacion/auditor Etapa 1 194 tests OK; `manage.py check` OK; migraciones dry-run OK; readiness local Etapa 1 diagnostica OK; `npm ci` 0 vulnerabilidades; build/lint OK; acceptance local 1309 tests OK; higiene repo y `git diff --check` OK. |
| Bloqueos relacionados | BLK-002 sigue abierto para cierre evidencial de Etapa 1; este paquete solo prepara validadores internos y metadata canonica sin fuente real/controlada. |
| Politica de reanudacion | Si no hay worktree tactico de producto abierto, diagnosticar desde `main` limpio y elegir el siguiente frente util por orden de construccion, trazabilidad, stage cards y evidencia vigente. El rescue pausado no habilita lectura de datos reales ni bloquea trabajo local seguro. |
| Siguiente accion | Tras mergear y limpiar este paquete, confirmar `git status --short --branch` y `git worktree list`, diagnosticar el siguiente frente seguro por orden de construccion/trazabilidad y abrir un worktree `codex/...` solo cuando haya paquete concreto. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
