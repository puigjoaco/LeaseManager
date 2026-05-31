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
| Frente activo | Etapa 2 - atomicidad de auditoria en APIs de CobranzaActiva. |
| Fuente exacta | Estado real de `main` en `e9fd0a5` despues de PR #611, stage cards, trazabilidad, evidencia y bloqueos vigentes. |
| Brecha activa | `backend/cobranza/views.py` persiste algunas mutaciones de Cobranza antes de crear la auditoria de vista. Si falla la auditoria, podrian quedar pagos, ajustes, garantias, repactaciones, UF o estados de cuenta mutados sin traza transaccional de la API. |
| Motivo de prioridad | Tras cerrar la atomicidad equivalente en Contratos, CobranzaActiva es el siguiente frente del orden de construccion con brecha local, verificable y sin dependencia de fuentes externas. |
| Worktree | `D:/Proyectos/LeaseManager-stage2-cobranza-audit-atomicity`. |
| Rama | `codex/stage2-cobranza-audit-atomicity`. |
| Estado | Paquete tactico abierto. |
| Gate esperado | Tests focales de rollback API, suite impactada Cobranza/Etapa 2, `manage.py check`, migraciones dry-run, gate local Etapa 2 diagnostico, frontend build/lint, acceptance local, higiene y CI GitHub. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Los cierres evidenciales que requieran fuente `snapshot_controlado`, datos reales o integraciones externas siguen siendo condiciones de cierre, no prerequisito para este paquete local. |
| Politica de reanudacion | Si este worktree aparece sucio, terminar o pausar este paquete antes de abrir otro frente. Si no existe, confirmar el cursor actualizado en `main` antes de diagnosticar el siguiente frente. |
| Siguiente accion | Completar implementacion, pruebas focales, documentacion/evidencia, validaciones proporcionales, PR, CI, merge y limpieza. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
