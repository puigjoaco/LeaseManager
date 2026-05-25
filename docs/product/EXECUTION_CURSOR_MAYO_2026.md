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
| Frente activo | Etapa 2 - CobranzaActiva, score de pago en estado de cuenta del arrendatario. |
| Fuente exacta | PRD `01_Set_Vigente/PRD_CANONICO.md` lineas 111-112 y 231; `docs/product/STAGE_CARDS/ETAPA_2_COBRANZA_CANALES.md`; `backend/cobranza/services.py`; `backend/cobranza/models.py`; `backend/core/stage2_cobranza_readiness.py`; tests de Cobranza y readiness Etapa 2. |
| Brecha activa | `EstadoCuentaArrendatario.score_pago` existe, pero el recalculo del estado de cuenta no calcula ni persiste porcentaje, conteo de meses evaluados ni cumplimiento en plazo segun pagos operativos; readiness tampoco detecta scores heredados faltantes o desactualizados. |
| Motivo de prioridad | Regla local del PRD sobre estado de cuenta y score de pago; no requiere `.env`, secretos, DB historica, datos reales ni integraciones externas. |
| Worktree | `D:/Proyectos/LeaseManager-stage2-account-payment-score`. |
| Rama | `codex/stage2-account-payment-score`. |
| Estado | Implementado y validado localmente; pendiente de commit, PR, CI, merge y limpieza. |
| Gate esperado | Etapa 2 local queda como diagnostico parcial/no evidencial; no cierra sin fuente autorizada, evidencia Etapa 1 y pruebas Email/WebPay controladas. |
| Estado al cerrar paquete | Pendiente de abrir PR, esperar CI, mergear y limpiar worktree tactico. |
| Bloqueos relacionados | Fuente autorizada de Etapa 2, evidencia Etapa 1 y pruebas externas controladas siguen siendo condicion de cierre real, no de preparacion local. |
| Politica de reanudacion | Confirmar estado real con `git status --short --branch` y `git worktree list`; si no hay worktree tactico abierto, elegir el siguiente paquete seguro por trazabilidad. |
| Siguiente accion | Empaquetar el cambio, abrir PR, esperar CI, mergear y limpiar worktree tactico. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
