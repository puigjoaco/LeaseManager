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
| Frente activo | Etapa 1 / Contratos |
| Fuente exacta | `01_Set_Vigente/PRD_CANONICO.md` lineas 340-341 |
| Brecha activa | Contratos retroactivos no reconstruyen pagos/cobros pasados automaticos y alertan posible notificacion manual si se registran despues del dia 5 del mes operativo. |
| Motivo de prioridad | Es una regla local del PRD, no requiere secretos, `.env`, DB historica, snapshot ni integracion externa. |
| Worktree | `D:/Proyectos/LeaseManager-retroactive-contract-alert` |
| Rama | `codex/retroactive-contract-alert` |
| Estado | Parcial, sin commit; contiene cambios en `backend/contratos/models.py`, `backend/contratos/serializers.py` y `backend/contratos/views.py`. |
| Gate esperado | Migracion Django, tests focales de contratos/cobranza/auditor Etapa 1, `manage.py check`, `makemigrations --check --dry-run`, readiness local Etapa 1, build frontend si toca UI, acceptance proporcional o completa, higiene repo y `git diff --check`. |
| Estado al cerrar paquete | `implementado_sin_evidencia`; no cierra Etapa 1 sin fuente `snapshot_controlado` o `real_autorizado`. |
| Bloqueos relacionados | `BLK-002` solo bloquea cierre evidencial de Etapa 1; no bloquea esta preparacion local. |
| Metatareas cerradas | Redaccion/revision del goal; repeticion de solicitud BLK-002; solicitud repetida de `.env`/`DATABASE_URL` sin peticion actual del usuario. |
| Siguiente accion | Completar o descartar de forma explicita el worktree `codex/retroactive-contract-alert` antes de abrir otro frente de producto. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una metatarea queda cerrada y no debe reabrirse en reanudaciones futuras.
