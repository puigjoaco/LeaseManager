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
| Frente activo | Sin paquete tactico abierto. |
| Fuente exacta | `main` limpio en `4890f654` despues de mergear PR #761; paquete `codex/stage2-overdue-global-state-sync` cerrado, rama remota borrada y worktree tactico removido. Rescue pausado fuera de alcance. |
| Brecha activa | Ninguna brecha activa fijada en cursor. El siguiente paquete debe diagnosticarse desde `main` limpio contra PRD, stage cards, trazabilidad, evidencia y bloqueos vigentes. |
| Motivo de prioridad | Evitar que reanudaciones o compactaciones reabran el paquete #761 ya cerrado. El cursor queda como control operativo de avance, no como lista de prompts o metatareas. |
| Worktree | Ninguno. |
| Rama | `main`. |
| Estado | Listo para seleccionar el siguiente frente util y seguro desde el repo limpio. |
| Gate esperado | El proximo paquete debe definir su gate proporcional antes de editar; los cierres evidenciales siguen sin declararse sin fuente autorizada y evidencia. |
| Estado al cerrar paquete | PR #761 mergeado; focal Cobranza OK; suite impactada Cobranza/readiness OK; `manage.py check` OK; migraciones dry-run OK; gate Etapa 2 parcial OK; frontend build/lint OK; acceptance local OK; CI remoto OK; merge y limpieza hechos. |
| Bloqueos relacionados | Los cierres evidenciales que dependan de fuentes externas siguen condicionados por autorizacion/fuente controlada y no bloquean trabajo local seguro. |
| Politica de reanudacion | Si no hay worktree tactico de producto abierto, diagnosticar desde `main` limpio y elegir el siguiente frente util por orden de construccion, trazabilidad, stage cards y evidencia vigente. El rescue pausado no habilita lectura de datos reales ni bloquea trabajo local seguro. |
| Siguiente accion | Desde `main` limpio, confirmar `git status --short --branch` y `git worktree list`, diagnosticar el siguiente frente seguro por orden de construccion/trazabilidad y abrir un worktree `codex/...` solo cuando haya paquete concreto. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
