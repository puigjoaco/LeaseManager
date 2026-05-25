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
| Frente activo | Ninguno. Ultimo paquete cerrado: Etapa 3 - Conciliacion, alineacion de periodo economico y fecha de cuadratura bancaria. |
| Fuente exacta | PR #229 `Guard Stage 3 balance square period alignment`; commit `fa92f56`; merge `557b054`; `backend/conciliacion/models.py`; `backend/core/stage3_conciliacion_readiness.py`; tests de Conciliacion/Stage 3; stage card, trazabilidad y evidencia actualizadas. |
| Brecha activa | Cerrada localmente: `CuadraturaBancaria` rechaza `periodo_economico` que no coincide con el mes de `fecha_cuadratura`, y readiness clasifica snapshots heredados con `stage3.balance_square.period_date_mismatch`. |
| Motivo de prioridad | Brecha local trazable de Conciliacion cerrada sin usar banco real, `.env`, datos reales ni integraciones externas. |
| Worktree | Ninguno. |
| Rama | `main` sincronizada con `origin/main` tras PR #229. |
| Estado | PR #229 integrado con CI remoto en verde; paquete tactico limpiado. |
| Gate esperado | Etapa 3 local queda como diagnostico parcial/no evidencial; no cierra Conciliacion sin banco real o snapshot autorizado, evidencia Etapa 2, prueba bancaria, cuadratura sistema/banco y responsable. |
| Estado al cerrar paquete | Cerrado e integrado en `main` con validacion local y CI remoto. |
| Bloqueos relacionados | Banco real/snapshot autorizado y evidencias externas siguen siendo condicion de cierre, no freno para este hardening local. |
| Politica de reanudacion | Confirmar estado real con `git status --short --branch` y `git worktree list`; si no hay worktree tactico abierto, elegir el siguiente paquete seguro por trazabilidad. |
| Siguiente accion | Seleccionar el siguiente frente util desde stage cards, matriz de trazabilidad y PRD, abrir worktree `codex/...` si corresponde y avanzar con validaciones proporcionales. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
