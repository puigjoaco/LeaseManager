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
| Frente activo | Etapa 3 - Conciliacion, match exacto de pagos acotado al periodo economico del movimiento bancario. |
| Fuente exacta | PRD `01_Set_Vigente/PRD_CANONICO.md` lineas 307, 384 y 427; `docs/product/STAGE_CARDS/ETAPA_3_BANCO_CONCILIACION.md`; `backend/conciliacion/services.py`; `backend/conciliacion/models.py`; `backend/core/stage3_conciliacion_readiness.py`; tests de Conciliacion y readiness Etapa 3. |
| Brecha activa | El match exacto automatico puede seleccionar un `PagoMensual` pendiente/atrasado por cuenta y monto sin acotar el periodo economico del movimiento al mes/anio del pago. Eso permite cerrar un abono de otro periodo sin pasar por resolucion manual. |
| Motivo de prioridad | Regla local del PRD sobre conciliacion por cuenta, contrato, periodo y arrendatario; no requiere `.env`, secretos, DB historica, datos reales ni integraciones externas. |
| Worktree | `D:/Proyectos/LeaseManager-stage3-exact-match-payment-period`. |
| Rama | `codex/stage3-exact-match-payment-period`. |
| Estado | Implementado y validado localmente; pendiente de commit, PR, CI, merge y limpieza. |
| Gate esperado | Etapa 3 local queda como diagnostico parcial/no evidencial; no cierra sin banco real o snapshot autorizado, evidencia Etapa 2, prueba bancaria y cuadratura controlada. |
| Estado al cerrar paquete | Pendiente de abrir PR, esperar CI, mergear y limpiar worktree tactico. |
| Bloqueos relacionados | Banco real o snapshot autorizado, evidencia Etapa 2, prueba bancaria, cuadratura sistema/banco y responsable siguen siendo condicion de cierre real, no de preparacion local. |
| Politica de reanudacion | Confirmar estado real con `git status --short --branch` y `git worktree list`; si no hay worktree tactico abierto, elegir el siguiente paquete seguro por trazabilidad. |
| Siguiente accion | Empaquetar el cambio, abrir PR, esperar CI, mergear y limpiar worktree tactico. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
