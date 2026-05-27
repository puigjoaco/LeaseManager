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
| Frente activo | Etapa 0 / Gobierno - higiene de artefactos locales. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | `.codex-spreadsheet/` aparece como artefacto local no versionado y ensucia `git status` del root limpio. |
| Motivo de prioridad | Mantener `main` limpio y evitar que artefactos locales de herramienta compitan con el cursor operativo o parezcan trabajo de producto. |
| Worktree | `D:/Proyectos/LeaseManager-governance-ignore-local-artifacts`. |
| Rama | `codex/governance-ignore-local-artifacts`. |
| Estado | Implementado localmente; `.codex-spreadsheet/` queda ignorado sin borrar el artefacto existente. |
| Gate esperado | Higiene repo, `git diff --check` y validacion proporcional sin tocar secretos ni datos reales. |
| Estado al cerrar paquete | Validacion local proporcional OK: `git check-ignore -v .codex-spreadsheet/`, `scripts/assert-repo-hygiene.ps1` y `git diff --check`. Pendiente PR, CI, merge y limpieza. |
| Bloqueos relacionados | Sin bloqueo externo nuevo. |
| Politica de reanudacion | Si no existe worktree tactico sucio, tomar el siguiente frente seguro desde trazabilidad y abrirlo explicitamente en este cursor. |
| Siguiente accion | Validar que `.codex-spreadsheet/` quede ignorado, actualizar evidencia y cerrar paquete con PR/CI/merge/limpieza. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
