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
| Frente activo | Sin paquete tactico abierto; ultimo cierre Etapa 5 - Eventos contables para transferencias intercuenta. |
| Fuente exacta | PR #201 `Guard Stage 5 internal transfer accounting events`, merge `85f9976`, desde `01_Set_Vigente/PRD_CANONICO.md` lineas 191, 194, 235, 241-243, 294, 377, 387, 429, 434 y 435; `docs/product/STAGE_CARDS/ETAPA_5_CIERRE_MENSUAL_CONTABILIDAD.md`. |
| Brecha activa | Cerrada localmente: `TransferenciaIntercuenta` conciliada alimenta eventos contables idempotentes de salida/entrada y readiness Etapa 5 bloquea transferencias de empresa sin esos eventos. |
| Motivo de prioridad | Conciliacion ya distingue transferencias intercuenta; Contabilidad ahora recibe el hecho trazable antes de cierre mensual, sin banco real ni datos externos. |
| Worktree | Ninguno activo; solo debe existir `D:/Proyectos/LeaseManager` salvo que se abra el siguiente frente. |
| Rama | `main` sincronizada; sin rama tactica activa. |
| Estado | PR #201 integrado en `main`, CI `acceptance` verde, worktree/rama tactica eliminados. |
| Gate esperado | Sin gate pendiente para este paquete; seleccionar el siguiente frente local seguro desde `main` limpio. |
| Estado al cerrar paquete | `implementado_sin_evidencia`; no cierra Etapa 5 sin Conciliacion cerrada, fuente `snapshot_controlado` o `real_autorizado`, ledger/reportes controlados y responsable. |
| Bloqueos relacionados | `BLK-003` y dependencias de cierre contable no bloquean preparacion local; solo impiden cierre evidencial. |
| Metatareas cerradas | Redaccion/revision del goal; repeticion de solicitud BLK-002; solicitud repetida de `.env`/`DATABASE_URL` sin peticion actual del usuario. |
| Siguiente accion | Desde `main` limpio, seleccionar el siguiente paquete util y seguro segun AGENTS.md, PRD canonico, stage cards y trazabilidad vigente. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una metatarea queda cerrada y no debe reabrirse en reanudaciones futuras.
