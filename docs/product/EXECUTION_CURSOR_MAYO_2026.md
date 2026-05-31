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
| Frente activo | Etapa 5 - atomicidad de mutaciones API de Contabilidad y auditoria. |
| Fuente exacta | Estado real de `main` en `297d6fd` despues de PR #615, stage cards, trazabilidad, evidencia y bloqueos vigentes. |
| Brecha activa | `backend/contabilidad/views.py` guarda entidades, contabiliza eventos o prepara/aprueba/reabre cierres y luego registra auditoria de vista fuera de la misma transaccion. Si falla esa auditoria, pueden quedar cambios contables sin traza del endpoint que los ejecuto. |
| Motivo de prioridad | Contabilidad sigue a Conciliacion en el orden de construccion y la brecha es local, verificable y no depende de banco real, SII, snapshots autorizados ni datos reales. |
| Worktree | `D:/Proyectos/LeaseManager-stage5-accounting-audit-atomicity`. |
| Rama | `codex/stage5-accounting-audit-atomicity`. |
| Estado | Paquete tactico abierto. |
| Gate esperado | Tests focales de rollback ante falla de auditoria, suite impactada Contabilidad/Etapa 5/Reporting, `manage.py check`, migraciones dry-run, gate local Etapa 5 diagnostico, frontend build/lint, acceptance local, higiene y CI GitHub. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | El cierre evidencial de Etapa 5 sigue condicionado por Conciliacion cerrada, fuente autorizada/controlada, evidencia ledger/reportes y validaciones externas aplicables. Este paquete local no usa `.env`, secretos, DB historicas, datos reales, snapshots autorizados, backfills, deploys ni integraciones externas. |
| Politica de reanudacion | Si este worktree aparece sucio, terminar o pausar este paquete antes de abrir otro frente. Si no existe, confirmar el cursor actualizado en `main` antes de diagnosticar el siguiente frente. |
| Siguiente accion | Implementar atomicidad, pruebas focales, documentacion/evidencia, validaciones proporcionales, PR, CI, merge y limpieza. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
