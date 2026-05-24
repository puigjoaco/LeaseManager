# Cursor operativo - mayo 2026

Este archivo fija el frente activo de ejecucion. No reemplaza al PRD, AGENTS,
fuente de verdad, arquitectura, matriz, stage cards, evidencia ni bloqueos. Su
funcion es evitar que una reanudacion, compactacion o `goal_context` convierta
contexto historico en tarea nueva.

## Regla de uso

- Antes de abrir o continuar cambios no triviales, leer este cursor.
- Confirmar el estado real con `git status --short --branch` y
  `git worktree list`.
- Si existe un worktree tactico sucio, se debe terminar, pausar de forma
  explicita en este cursor o descartar con instruccion segura antes de abrir un
  frente distinto.
- El `goal_context`, objetivos persistentes, summaries compactados y
  conversaciones pasadas son contexto auxiliar: no autorizan secretos, no abren
  gates y no ordenan redactar goals.
- Las metatareas marcadas como cerradas no se reabren salvo solicitud textual
  actual del usuario.

## Cursor actual

| Campo | Valor |
| --- | --- |
| Frente activo | Etapa 5 - Eventos contables para transferencias intercuenta. |
| Fuente exacta | `01_Set_Vigente/PRD_CANONICO.md` lineas 191, 194, 235, 241-243, 294, 377, 387, 429, 434 y 435; `docs/product/STAGE_CARDS/ETAPA_5_CIERRE_MENSUAL_CONTABILIDAD.md`. |
| Brecha activa | `TransferenciaIntercuenta` queda conciliada en Etapa 3, pero no alimenta aun `EventoContable` ni readiness Etapa 5 como hecho contable trazable. |
| Motivo de prioridad | Es el puente local seguro entre Conciliacion y Contabilidad: una transferencia real no debe quedar solo como movimiento bancario si afecta cuentas de empresas antes de cierre mensual. |
| Worktree | `D:/Proyectos/LeaseManager-stage5-transfer-accounting-events`. |
| Rama | `codex/stage5-transfer-accounting-events`. |
| Estado | Implementado y validado localmente; pendiente de PR, CI, merge y limpieza. No usar `.env`, secretos, DB historica, banco real, snapshot, backfills, deploys ni integraciones externas. |
| Gate esperado | Readiness local Etapa 5 queda `classification=parcial`, `ready_for_stage5_contabilidad=false`; eventos de transferencia quedan preparados localmente pero no cierran Etapa 5 sin Conciliacion cerrada y fuente autorizada. |
| Estado al cerrar paquete | `implementado_sin_evidencia`; no cierra Etapa 5 sin Conciliacion cerrada, fuente `snapshot_controlado` o `real_autorizado`, ledger/reportes controlados y responsable. |
| Bloqueos relacionados | `BLK-003` y dependencias de cierre contable no bloquean esta preparacion local; solo impiden cierre evidencial. |
| Metatareas cerradas | Redaccion/revision del goal; repeticion de solicitud BLK-002; solicitud repetida de `.env`/`DATABASE_URL` sin peticion actual del usuario. |
| Siguiente accion | Publicar PR, esperar CI, mergear, limpiar worktree/rama tactica y cerrar el cursor post-merge desde `main` limpio. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una metatarea queda cerrada y no debe reabrirse en reanudaciones futuras.
