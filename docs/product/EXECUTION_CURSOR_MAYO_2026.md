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
| Frente activo | Ninguno. Ultimo paquete cerrado: Etapa 2 - CobranzaActiva, pagos originales trazables a repactaciones. |
| Fuente exacta | PR #258, commit `c187f29`, merge `96ae62f`; PRD `01_Set_Vigente/PRD_CANONICO.md` lineas 362 y 416; `docs/product/STAGE_CARDS/ETAPA_2_COBRANZA_CANALES.md`; `backend/cobranza/models.py`; `backend/cobranza/serializers.py`; `backend/cobranza/services.py`; `backend/core/stage2_cobranza_readiness.py`; evidencia y trazabilidad. |
| Brecha activa | Cerrada localmente: `PagoMensual` enlaza la `RepactacionDeuda` que explica estados `en_repactacion` y `pagado_via_repactacion`, conserva `dias_mora`, valida contrato/arrendatario/estado del plan, expone el enlace en API/snapshot y readiness Etapa 2 bloquea snapshots heredados sin plan trazable o con plan incompatible. |
| Motivo de prioridad | Paquete de CobranzaActiva derivado del PRD, cerrado con validacion local, CI y merge sin `.env`, secretos, DB historica, datos reales ni integraciones externas. |
| Worktree | Ninguno. Solo debe quedar el worktree principal. |
| Rama | `main` sincronizada con `origin/main` despues de PR #258. |
| Estado | Listo para reanudacion operativa desde el siguiente paquete de producto seguro. |
| Gate esperado | Etapa 2 local queda como diagnostico parcial/no evidencial; no cierra sin fuente autorizada, evidencia Etapa 1 y pruebas Email/WebPay controladas. |
| Estado al cerrar paquete | Validado, PR #258 mergeado con CI acceptance verde y worktree tactico eliminado. |
| Bloqueos relacionados | Fuente autorizada de Etapa 2, evidencia Etapa 1 y pruebas externas controladas siguen siendo condicion de cierre real, no de preparacion local. |
| Politica de reanudacion | Confirmar estado real con `git status --short --branch` y `git worktree list`; si no hay worktree tactico abierto, elegir el siguiente paquete seguro por trazabilidad. |
| Siguiente accion | Seleccionar el siguiente paquete seguro desde stage cards, trazabilidad y PRD; abrir worktree `codex/...` si el cambio no es trivial. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
