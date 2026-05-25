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
| Frente activo | Ninguno. Ultimo paquete cerrado: Etapa 3 - Conciliacion, pagos parciales o complementarios requieren resolucion manual auditada. |
| Fuente exacta | PR #264; commit `0eaf147`; merge `962d1e9`. PRD `01_Set_Vigente/PRD_CANONICO.md` lineas 382-387; `docs/product/STAGE_CARDS/ETAPA_3_BANCO_CONCILIACION.md`; `backend/core/stage3_conciliacion_readiness.py`; tests de readiness Etapa 3. |
| Brecha activa | Ninguna abierta en cursor. La brecha de abonos parciales conciliados sin resolucion manual quedo corregida y validada en PR #264. |
| Motivo de prioridad | Paquete cerrado porque reforzo una regla local de conciliacion: pagos parciales, complementarios o en varios abonos solo pueden sumarse con regla segura, suma exacta y resolucion manual auditada. No requirio `.env`, secretos, DB historica, datos reales ni integraciones externas. |
| Worktree | Ninguno tactico abierto. |
| Rama | Ninguna tactica abierta. |
| Estado | PR #264 mergeado, CI `acceptance` en verde, main sincronizado y worktree tactico eliminado. |
| Gate esperado | Etapa 3 sigue como diagnostico parcial/no evidencial; no cierra sin banco real o snapshot autorizado, evidencia Etapa 2, prueba bancaria y cuadratura controlada. |
| Estado al cerrar paquete | Cerrado en main con merge `962d1e9`; siguiente frente debe elegirse por trazabilidad desde estado limpio. |
| Bloqueos relacionados | Banco real o snapshot autorizado, evidencia Etapa 2, prueba bancaria, cuadratura sistema/banco y responsable siguen siendo condicion de cierre real, no de preparacion local. |
| Politica de reanudacion | Confirmar estado real con `git status --short --branch` y `git worktree list`; si no hay worktree tactico abierto, elegir el siguiente paquete seguro por trazabilidad. |
| Siguiente accion | Confirmar estado real con `git status --short --branch` y `git worktree list`; si no hay worktree tactico abierto, elegir el siguiente paquete seguro por trazabilidad. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
