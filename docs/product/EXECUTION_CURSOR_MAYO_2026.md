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
| Frente activo | Etapa 2 - Canales/Cobranza. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | Redaccion consistente de `restricciones_operativas` en gates de Canales y Cobranza. |
| Motivo de prioridad | Stage cards y trazabilidad exigen que API, snapshot y admin expongan restricciones operativas heredadas solo como payload redactado; Canales preservaba claves canonicas pero no redactaba claves sensibles no autorizadas en API/snapshot, y Cobranza no redactaba/incluia restricciones de gate en todas las superficies. |
| Worktree | `D:/Proyectos/LeaseManager-stage2-gate-restrictions-redaction`. |
| Rama | `codex/stage2-gate-restrictions-redaction`. |
| Estado | En implementacion. |
| Gate esperado | Tests focales Canales/Cobranza, suite impactada Etapa 2, `manage.py check`, migraciones dry-run, gate Etapa 2 local, frontend build/lint si aplica, acceptance local, higiene repo, diff check y CI remoto. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Sin bloqueo externo nuevo. |
| Politica de reanudacion | Continuar este worktree hasta PR/CI/merge/limpieza o pausar explicitamente en este cursor. |
| Siguiente accion | Completar implementacion, validar y cerrar el paquete. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
