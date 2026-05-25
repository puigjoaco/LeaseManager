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
| Frente activo | Etapa 2 - CobranzaActiva, excepcion formal para repactacion parcial. |
| Fuente exacta | PRD `01_Set_Vigente/PRD_CANONICO.md` linea 358; `docs/product/STAGE_CARDS/ETAPA_2_COBRANZA_CANALES.md`; `backend/cobranza/models.py`; `backend/cobranza/serializers.py`; `backend/core/stage2_cobranza_readiness.py`; `backend/cobranza/tests.py`; `backend/core/tests_stage2_cobranza_readiness.py`. |
| Brecha activa | En curso: una repactacion parcial no debe pasar como plan ordinario; debe requerir referencia de excepcion formal no sensible, motivo auditable y deteccion de snapshots heredados sin esa traza. |
| Motivo de prioridad | Brecha de CobranzaActiva derivada del PRD, verificable localmente sin `.env`, secretos, DB historica, datos reales ni integraciones externas. |
| Worktree | `D:/Proyectos/LeaseManager-stage2-partial-repayment-exception`. |
| Rama | `codex/stage2-partial-repayment-exception`. |
| Estado | En diagnostico e implementacion local. |
| Gate esperado | Etapa 2 local queda como diagnostico parcial/no evidencial; no cierra sin fuente autorizada, evidencia Etapa 1 y pruebas Email/WebPay controladas. |
| Estado al cerrar paquete | Pendiente de implementacion, validacion, PR, CI, merge y limpieza. |
| Bloqueos relacionados | Fuente autorizada de Etapa 2, evidencia Etapa 1 y pruebas externas controladas siguen siendo condicion de cierre real, no de preparacion local. |
| Politica de reanudacion | Confirmar estado real con `git status --short --branch` y `git worktree list`; si no hay worktree tactico abierto, elegir el siguiente paquete seguro por trazabilidad. |
| Siguiente accion | Implementar guard de dominio/API/readiness para repactacion parcial, validar Cobranza/Etapa 2, abrir PR, esperar CI, mergear, limpiar worktree y cerrar cursor. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
