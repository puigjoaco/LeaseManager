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
| Frente activo | PlataformaBase / Core migration pipeline. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | `core.tests_migration_pipeline` falla en resoluciones de comunidad mixta porque la participacion empresa creada por el pipeline no satisface la validacion vigente de `participante_empresa`. |
| Motivo de prioridad | Recupera una suite Core amplia como gate util y evita que una validacion patrimonial reciente deje roto el flujo controlado de migracion local. |
| Worktree | `D:/Proyectos/LeaseManager-core-migration-company-participant`. |
| Rama | `codex/core-migration-company-participant`. |
| Estado | Implementado y validado localmente; pendiente commit, PR, CI, merge y limpieza. |
| Gate esperado | Tests focales de `core.tests_migration_pipeline`, suite `core`, `manage.py check`, migraciones dry-run, frontend build/lint si aplica, acceptance local, higiene. |
| Estado al cerrar paquete | Pendiente de merge. |
| Bloqueos relacionados | Sin bloqueo externo nuevo. |
| Politica de reanudacion | Continuar este worktree hasta PR/CI/merge/limpieza antes de abrir otro paquete. |
| Siguiente accion | Commit, PR, CI, merge y limpieza del worktree tactico. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
