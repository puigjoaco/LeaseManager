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
| Frente activo | Etapa 3 - Transferencias internas/intercuenta trazadas. |
| Fuente exacta | `01_Set_Vigente/PRD_CANONICO.md` lineas 191, 294, 387, 429 y 435; `docs/product/ANEXO_MODELO_OPERATIVO_EXCEL_MAYO_2026.md` lineas 95-96, 171, 181 y 197. |
| Brecha activa | `CategoriaMovimiento.INTERNAL_TRANSFER` existe, pero Conciliacion no registra todavia un par cargo/abono intercuenta con evidencia, owner origen/destino y readiness bloqueante. |
| Motivo de prioridad | Es el siguiente frente seguro despues de CobranzaActiva: Conciliacion debe distinguir cargo bancario, ingreso desconocido y transferencia real antes de alimentar Contabilidad, sin banco real ni datos externos. |
| Worktree | `D:/Proyectos/LeaseManager-stage3-internal-transfer-readiness`. |
| Rama | `codex/stage3-internal-transfer-readiness`. |
| Estado | Implementado y validado localmente; pendiente commit, PR, CI, merge y limpieza del worktree tactico. No usar `.env`, secretos, DB historica, banco real, snapshot, backfills, deploys ni integraciones externas. |
| Gate esperado | Readiness local Etapa 3 queda `classification=parcial`, `ready_for_stage3_conciliacion=false`; las transferencias internas quedan auditadas localmente pero no cierran Etapa 3 sin fuente autorizada. |
| Estado al cerrar paquete | Pendiente de integracion; el paquete deja transferencias intercuenta auditables como preparacion local segura, sin cerrar Etapa 3. |
| Bloqueos relacionados | `BLK-003` no bloquea esta preparacion local; solo impide cierre evidencial o conexion bancaria real. |
| Metatareas cerradas | Redaccion/revision del goal; repeticion de solicitud BLK-002; solicitud repetida de `.env`/`DATABASE_URL` sin peticion actual del usuario. |
| Siguiente accion | Publicar PR de `codex/stage3-internal-transfer-readiness`, esperar CI, mergear, limpiar worktree y actualizar `main`. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una metatarea queda cerrada y no debe reabrirse en reanudaciones futuras.
