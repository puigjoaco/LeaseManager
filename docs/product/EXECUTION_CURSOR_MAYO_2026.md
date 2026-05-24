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
| Frente activo | Etapa 2 - Traza de fallback para WhatsApp bloqueado/fallido. |
| Fuente exacta | `01_Set_Vigente/PRD_CANONICO.md` lineas 119-122 y `docs/product/STAGE_CARDS/ETAPA_2_COBRANZA_CANALES.md`: WhatsApp opera solo con opt-in/template/ventana, y una falla no debe dejar sin canal base o alerta critica. |
| Brecha activa | En implementacion local: Canales debe registrar fallback Email/alerta critica cuando WhatsApp queda bloqueado, y readiness Etapa 2 debe detectar mensajes heredados bloqueados o fallidos sin esa traza. |
| Motivo de prioridad | Cierra una brecha local de Canales sin abrir WhatsApp, Email real, WebPay, secretos, `.env`, DB historica, snapshot, backfills, deploys ni integraciones externas. |
| Worktree | `D:/Proyectos/LeaseManager-stage2-whatsapp-fallback-trace`. |
| Rama | `codex/stage2-whatsapp-fallback-trace`. |
| Estado | Implementacion y validacion local en curso. |
| Gate esperado | Readiness local Etapa 2 como diagnostico parcial; no ejecutar proveedores ni fuente evidencial sin autorizacion actual. |
| Estado al cerrar paquete | Pendiente; esperado `implementado_sin_evidencia` si PR/CI/merge quedan verdes. |
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
