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
| Frente activo | Sin paquete tactico abierto; ultimo cierre Etapa 2 - Refresco local de mora para pagos abiertos vencidos. |
| Fuente exacta | PR #197 `Guard Stage 2 overdue refresh readiness`, merge `1015031`, desde `01_Set_Vigente/PRD_CANONICO.md` lineas 29, 229, 416 y 456. |
| Brecha activa | Cerrada localmente: pagos `pendiente` con `fecha_vencimiento` pasada se refrescan como `atrasado`, recalculan `dias_mora`, sincronizan estado de cuenta y quedan bloqueados por readiness si siguen stale. |
| Motivo de prioridad | La mora ya no depende solo de pago/deteccion posterior; CobranzaActiva tiene una operacion local reproducible antes de Email/WebPay/banco real, sin usar secretos, `.env`, DB historica, snapshot, backfills, deploys ni integraciones externas. |
| Worktree | Ninguno activo; solo debe existir `D:/Proyectos/LeaseManager` salvo que se abra el siguiente frente. |
| Rama | `main` sincronizada; sin rama tactica activa. |
| Estado | PR #197 integrado en `main`, CI `acceptance` verde, worktree/rama tactica eliminados. |
| Gate esperado | Sin gate pendiente para este paquete; seleccionar el siguiente frente local seguro desde `main` limpio. |
| Estado al cerrar paquete | `implementado_sin_evidencia`; no cierra Etapa 2 sin fuente `snapshot_controlado` o `real_autorizado`, pruebas Email/WebPay y responsables no sensibles. |
| Bloqueos relacionados | `BLK-002` no bloquea esta preparacion local; solo impide cierres evidenciales que requieran fuente autorizada. |
| Metatareas cerradas | Redaccion/revision del goal; repeticion de solicitud BLK-002; solicitud repetida de `.env`/`DATABASE_URL` sin peticion actual del usuario. |
| Siguiente accion | Desde `main` limpio, seleccionar el siguiente paquete util y seguro segun AGENTS.md, PRD canonico, stage cards y trazabilidad vigente. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una metatarea queda cerrada y no debe reabrirse en reanudaciones futuras.
