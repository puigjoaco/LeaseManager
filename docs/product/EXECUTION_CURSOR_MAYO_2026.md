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
| Frente activo | Etapa 5 - Contabilidad: validacion de empresa en movimientos de asiento. |
| Fuente exacta | `docs/product/STAGE_CARDS/ETAPA_5_CIERRE_MENSUAL_CONTABILIDAD.md`; `docs/product/TRACEABILITY_MATRIX_MAYO_2026.md` fila `Contabilidad`; `backend/contabilidad/models.py`; `backend/core/stage5_contabilidad_readiness.py`; tests de Contabilidad/Stage 5. |
| Brecha activa | `audit_stage5_contabilidad_readiness` y cierre mensual detectan movimientos de asiento asociados a cuentas de otra empresa, pero `MovimientoAsiento.clean()` aun no impide nuevas escrituras con esa incoherencia. |
| Motivo de prioridad | Brecha local trazable de Contabilidad; evita crear nuevos defectos de ledger que ya son bloqueantes en readiness sin usar `.env`, datos reales, banco, SII ni integraciones externas. |
| Worktree | `D:/Proyectos/LeaseManager-stage5-movement-account-company-clean`. |
| Rama | `codex/stage5-movement-account-company-clean`. |
| Estado | En implementacion. `main` queda limpio en `D:/Proyectos/LeaseManager`. |
| Gate esperado | Etapa 5 local queda como diagnostico parcial/no evidencial; no cierra Contabilidad sin Conciliacion cerrada, fuente autorizada, ledger/reportes controlados y responsable. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Conciliacion cerrada y fuente autorizada siguen siendo condicion de cierre, no freno para este hardening local. |
| Politica de reanudacion | Retomar este worktree hasta cerrar, pausar explicitamente en este cursor o limpiar con instruccion segura. |
| Siguiente accion | Agregar validacion de empresa en `MovimientoAsiento.clean()`, cubrirla con prueba focal, validar suite impactada y actualizar evidencia/trazabilidad. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
