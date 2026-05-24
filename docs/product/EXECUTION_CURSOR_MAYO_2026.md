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
| Frente activo | Etapa 2 - Cadencias de notificacion por contrato y canal habilitado. |
| Fuente exacta | `01_Set_Vigente/PRD_CANONICO.md` linea 118 y `docs/product/STAGE_CARDS/ETAPA_2_COBRANZA_CANALES.md`. |
| Brecha activa | En implementacion local: configurar dias de notificacion por contrato/canal, base sugerida `1/3/5/10/15/20/25`, sin enviar Email/WhatsApp ni abrir proveedores. |
| Motivo de prioridad | Cierra una regla PRD local de Cobranza/Canales que no depende de `.env`, datos reales, DB historica, snapshot, backfills, deploys ni integraciones externas. |
| Worktree | `D:/Proyectos/LeaseManager-stage2-notification-cadence`. |
| Rama | `codex/stage2-notification-cadence`. |
| Estado | Paquete tactico abierto; requiere validaciones proporcionales, PR, CI, merge y limpieza. |
| Gate esperado | `audit_stage2_cobranza_readiness` debe quedar `classification=parcial` en fuente local, detectando cadencias faltantes/invalidas sin cerrar Etapa 2. |
| Estado al cerrar paquete | Pendiente; debe quedar `implementado_sin_evidencia` y no cerrar Etapa 2 sin fuente `snapshot_controlado` o `real_autorizado`, pruebas Email/WebPay y responsables no sensibles. |
| Bloqueos relacionados | `BLK-002` solo bloquea cierre evidencial de Etapa 1; no bloquea esta preparacion local. |
| Metatareas cerradas | Redaccion/revision del goal; repeticion de solicitud BLK-002; solicitud repetida de `.env`/`DATABASE_URL` sin peticion actual del usuario. |
| Siguiente accion | Desde `main` limpio, seleccionar el siguiente paquete util y seguro segun AGENTS.md, PRD canonico, stage cards y trazabilidad vigente. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una metatarea queda cerrada y no debe reabrirse en reanudaciones futuras.
