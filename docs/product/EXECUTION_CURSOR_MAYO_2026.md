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
| Fuente exacta | Estado real de `main` en `e1e390d`, `docs/product/TRACEABILITY_MATRIX_MAYO_2026.md`, stage cards, evidencia y bloqueos vigentes. |
| Brecha activa | Ninguna en curso. El paquete Etapa 5 / Contabilidad / liquidaciones mensuales trazables quedo cerrado en PR #555. |
| Motivo de prioridad | Evitar que una reanudacion reabra un paquete ya integrado; el siguiente avance debe diagnosticarse desde `main` limpio y la trazabilidad vigente. |
| Worktree | Ninguno. Solo debe existir el worktree principal salvo apertura explicita del siguiente frente. |
| Rama | `main`. |
| Estado | PR #555 integrado en `main` con merge `e1e390d`; worktree tactico y rama `codex/stage5-monthly-liquidations` eliminados. |
| Gate esperado | Para el proximo paquete, definir gates proporcionales segun frente, archivos tocados y riesgo. |
| Estado al cerrar paquete | Etapa 5 / liquidaciones mensuales: commit `ce69111`; PR #555; CI acceptance pass; validacion local OK: focal 6 tests, suite impactada 96 tests, `manage.py check`, `makemigrations --check --dry-run`, gate Etapa 5 local parcial esperado, `npm ci`, `npm run build`, `npm run lint`, acceptance local 1092 tests, higiene repo y `git diff --check`. |
| Bloqueos relacionados | Sin bloqueo externo nuevo; Etapa 5 no se declara cerrada sin Conciliacion cerrada y fuente `snapshot_controlado` o `real_autorizado`. |
| Politica de reanudacion | Si `git status` y `git worktree list` muestran solo `main` limpio, diagnosticar el siguiente frente seguro; si aparece un worktree sucio, terminar o pausar ese paquete antes de abrir otro frente. |
| Siguiente accion | Diagnosticar el siguiente frente seguro desde el estado real del repo. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
