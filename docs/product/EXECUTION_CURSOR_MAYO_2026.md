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
| Frente activo | Etapa 2 - Programacion local de recordatorios de cobranza desde cadencias activas. |
| Fuente exacta | PRD canonico linea 306: enviar cobros y recordatorios por canales habilitados; continuidad del paquete PR #193 de cadencias de notificacion. |
| Brecha activa | En implementacion: `PagoMensual` pendiente/atrasado debe materializar recordatorios locales por pago/canal/dia, exponerlos en API/snapshot/backoffice y bloquear readiness si faltan o son invalidos. |
| Motivo de prioridad | La cadencia ya existe, pero sin programacion trazable los recordatorios quedan como configuracion inerte. Este paquete prepara el ciclo sin abrir Email, WhatsApp, WebPay, secretos, `.env`, DB historica, snapshot, backfills, deploys ni integraciones externas. |
| Worktree | `D:/Proyectos/LeaseManager-stage2-notification-schedule`. |
| Rama | `codex/stage2-notification-schedule`. |
| Estado | En curso; pruebas focales iniciales OK con SQLite local controlado. |
| Gate esperado | Local/parcial: no cierra Etapa 2 sin fuente autorizada, prueba Email/WebPay y responsables no sensibles. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | `BLK-002` solo bloquea cierre evidencial de Etapa 1; no bloquea esta preparacion local. |
| Metatareas cerradas | Redaccion/revision del goal; repeticion de solicitud BLK-002; solicitud repetida de `.env`/`DATABASE_URL` sin peticion actual del usuario. |
| Siguiente accion | Completar implementacion, ejecutar validaciones proporcionales, actualizar evidencia y cerrar con PR/CI/merge/limpieza. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una metatarea queda cerrada y no debe reabrirse en reanudaciones futuras.
