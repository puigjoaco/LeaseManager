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
| Frente activo | PlataformaBase / Seguridad - claves sensibles en metadata transversal. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | El detector transversal de referencias sensibles no clasifica nombres de metadata como `authorization` o `private_key` cuando el valor es opaco, dejando posible exposicion en payloads heredados redactados por clave. |
| Motivo de prioridad | Frente local seguro de PlataformaBase: refuerza redaccion/auditoria de secretos sin tocar `.env`, datos reales, DB historicas, backfills, deploys ni integraciones externas. |
| Worktree | `D:/Proyectos/LeaseManager-core-sensitive-reference-keys`. |
| Rama | `codex/core-sensitive-reference-keys`. |
| Estado | Abierto para endurecer deteccion de claves sensibles transversales, tests, trazabilidad y evidencia. |
| Gate esperado | Tests focales Core/reference validation, suites impactadas Core/Audit/Compliance, `manage.py check`, migraciones dry-run, frontend build/lint, acceptance local, higiene repo y CI remoto. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Sin bloqueo externo nuevo. |
| Politica de reanudacion | Continuar este worktree hasta PR/CI/merge o pausar explicitamente aqui si aparece un bloqueo real. |
| Siguiente accion | Ajustar detector transversal, cubrir claves `authorization`/`private_key` con tests y cerrar paquete. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
