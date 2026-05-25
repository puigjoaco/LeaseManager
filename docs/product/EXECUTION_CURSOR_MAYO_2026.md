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
| Frente activo | Etapa 3 - Conciliacion: alineacion de periodo economico y fecha de cuadratura bancaria. |
| Fuente exacta | `docs/product/STAGE_CARDS/ETAPA_3_BANCO_CONCILIACION.md`; `docs/product/TRACEABILITY_MATRIX_MAYO_2026.md` fila `Conciliacion`; `backend/conciliacion/models.py`; `backend/core/stage3_conciliacion_readiness.py`; tests de Conciliacion/Stage 3. |
| Brecha activa | `CuadraturaBancaria` valida formato `YYYY-MM`, diferencia y refs, pero no impide que `periodo_economico` apunte a un mes distinto de `fecha_cuadratura`; readiness tampoco clasifica ese snapshot heredado explicitamente. |
| Motivo de prioridad | Brecha local trazable de Conciliacion; refuerza cuadratura sistema/banco sin usar banco real, `.env`, datos reales ni integraciones externas. |
| Worktree | `D:/Proyectos/LeaseManager-stage3-balance-square-period-alignment`. |
| Rama | `codex/stage3-balance-square-period-alignment`. |
| Estado | En implementacion. `main` queda limpio en `D:/Proyectos/LeaseManager`. |
| Gate esperado | Etapa 3 local queda como diagnostico parcial/no evidencial; no cierra Conciliacion sin banco real o snapshot autorizado, evidencia Etapa 2, prueba bancaria, cuadratura sistema/banco y responsable. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Banco real/snapshot autorizado y evidencias externas siguen siendo condicion de cierre, no freno para este hardening local. |
| Politica de reanudacion | Retomar este worktree hasta cerrar, pausar explicitamente en este cursor o limpiar con instruccion segura. |
| Siguiente accion | Validar periodo/fecha de `CuadraturaBancaria` en dominio/readiness, agregar pruebas focales y actualizar evidencia/trazabilidad. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
