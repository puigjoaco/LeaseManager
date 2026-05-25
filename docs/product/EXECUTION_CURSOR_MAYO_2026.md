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
| Frente activo | Etapa 3 - Conciliacion, pagos parciales o complementarios requieren resolucion manual auditada. |
| Fuente exacta | PRD `01_Set_Vigente/PRD_CANONICO.md` lineas 382-387; `docs/product/STAGE_CARDS/ETAPA_3_BANCO_CONCILIACION.md`; `backend/core/stage3_conciliacion_readiness.py`; tests de readiness Etapa 3. |
| Brecha activa | Readiness Etapa 3 no distingue un snapshot heredado donde un movimiento por monto parcial queda `conciliado_exacto` contra un `PagoMensual` sin resolucion manual asociada. |
| Motivo de prioridad | Regla local de conciliacion: pagos parciales, complementarios o en varios abonos solo pueden sumarse con regla segura, suma exacta y resolucion manual auditada. No requiere `.env`, secretos, DB historica, datos reales ni integraciones externas. |
| Worktree | `D:/Proyectos/LeaseManager-stage3-partial-payment-resolution`. |
| Rama | `codex/stage3-partial-payment-resolution`. |
| Estado | Implementado y validado localmente; pendiente de commit, PR, CI, merge y limpieza. |
| Gate esperado | Etapa 3 sigue como diagnostico parcial/no evidencial; no cierra sin banco real o snapshot autorizado, evidencia Etapa 2, prueba bancaria y cuadratura controlada. |
| Estado al cerrar paquete | Pendiente de commit, PR, CI, merge y limpieza. |
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
