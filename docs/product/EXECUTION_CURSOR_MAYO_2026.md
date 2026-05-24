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
| Frente activo | Etapa 1 - Autoridad operativa trazable de `MandatoOperacion`. |
| Fuente exacta | `01_Set_Vigente/PRD_CANONICO.md` linea 409: empresas, comunidades y mandatos que firman o comunican documentos deben tener representante/autoridad operativa vigente y trazable. |
| Brecha activa | En implementacion local: `MandatoOperacion` activo que autoriza comunicacion o facturacion debe conservar nombre, RUT valido normalizado y evidencia no sensible de autoridad operativa; API, snapshot, backoffice y auditor Etapa 1 deben cubrir datos heredados. |
| Motivo de prioridad | Cierra una brecha local de PRD sin usar secretos, `.env`, DB historica, snapshot, backfills, deploys ni integraciones externas. |
| Worktree | `D:/Proyectos/LeaseManager-stage1-mandate-operational-authority`. |
| Rama | `codex/stage1-mandate-operational-authority`. |
| Estado | Implementacion y validacion local en curso. |
| Gate esperado | Readiness local Etapa 1 como diagnostico no evidencial; no ejecutar snapshot/DB real sin autorizacion actual. |
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
