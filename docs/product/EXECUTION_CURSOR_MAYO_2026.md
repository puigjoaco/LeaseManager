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
| Frente activo | Etapa 2 - CobranzaActiva, pagos originales trazables a repactaciones. |
| Fuente exacta | PRD `01_Set_Vigente/PRD_CANONICO.md` lineas 362 y 416; `docs/product/STAGE_CARDS/ETAPA_2_COBRANZA_CANALES.md`; `backend/cobranza/models.py`; `backend/cobranza/serializers.py`; `backend/core/stage2_cobranza_readiness.py`; tests de Cobranza y readiness Etapa 2. |
| Brecha activa | Los estados `en_repactacion` y `pagado_via_repactacion` existen en `PagoMensual`, pero el pago original no queda enlazado a una `RepactacionDeuda` ni el readiness bloquea snapshots heredados con estados de repactacion sin plan trazable o con estado de plan incompatible. |
| Motivo de prioridad | Regla local del PRD sobre deuda repactada; no requiere `.env`, secretos, DB historica, datos reales ni integraciones externas. |
| Worktree | `D:/Proyectos/LeaseManager-stage2-repayment-origin-payments`. |
| Rama | `codex/stage2-repayment-origin-payments`. |
| Estado | Validado localmente; pendiente PR, CI, merge y limpieza. |
| Gate esperado | Etapa 2 local queda como diagnostico parcial/no evidencial; no cierra sin fuente autorizada, evidencia Etapa 1 y pruebas Email/WebPay controladas. |
| Estado al cerrar paquete | Implementado y validado localmente: focal 5 tests, suite impactada 107 tests, acceptance local 728 tests, frontend build, readiness Etapa 2 local, higiene repo y `git diff --check` OK. Pendiente PR/CI/merge/limpieza. |
| Bloqueos relacionados | Fuente autorizada de Etapa 2, evidencia Etapa 1 y pruebas externas controladas siguen siendo condicion de cierre real, no de preparacion local. |
| Politica de reanudacion | Confirmar estado real con `git status --short --branch` y `git worktree list`; si no hay worktree tactico abierto, elegir el siguiente paquete seguro por trazabilidad. |
| Siguiente accion | Implementar enlace `PagoMensual` -> `RepactacionDeuda` para estados de repactacion, cubrir validaciones de dominio/readiness y documentar evidencia/trazabilidad. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
