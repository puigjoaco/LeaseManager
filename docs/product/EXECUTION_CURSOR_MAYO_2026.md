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
| Frente activo | Ninguno. Ultimo paquete cerrado: Etapa 6 - Renta Anual, resumen anual tributario exige ano comercial consistente. |
| Fuente exacta | PR #266; commit `ae14890`; merge `9a17b63`. PRD `01_Set_Vigente/PRD_CANONICO.md` lineas 248, 312, 464 y 606; `docs/product/STAGE_CARDS/ETAPA_6_RENTA_ANUAL.md`; `backend/sii/models.py`; `backend/core/stage6_renta_anual_readiness.py`; tests SII y readiness Etapa 6. |
| Brecha activa | Ninguna abierta en cursor. La brecha de payloads anuales con `fiscal_year` desalineado contra `anio_tributario` quedo corregida y validada en PR #266. |
| Motivo de prioridad | Paquete cerrado porque reforzo una regla local de Renta Anual: `ProcesoRentaAnual`, DDJJ y F22 deben trazar al ano comercial inmediatamente anterior al ano tributario, y readiness detecta snapshots heredados desalineados. No requirio `.env`, secretos, DB historica, datos reales, certificados ni integraciones SII externas. |
| Worktree | Ninguno tactico abierto. |
| Rama | Ninguna tactica abierta. |
| Estado | PR #266 mergeado, CI `acceptance` en verde, main sincronizado y worktree tactico eliminado. |
| Gate esperado | Etapa 6 sigue como diagnostico parcial/no evidencial; no cierra sin fuente autorizada, doce cierres/snapshot controlado, regla fiscal validada, certificados/respaldos controlados y responsable tributario. |
| Estado al cerrar paquete | Cerrado en main con merge `9a17b63`; siguiente frente debe elegirse por trazabilidad desde estado limpio. |
| Bloqueos relacionados | Fuente `snapshot_controlado` o `real_autorizado`, doce cierres evidenciados, regla fiscal validada, certificados/respaldos controlados y responsable tributario siguen siendo condicion de cierre real, no de preparacion local. |
| Politica de reanudacion | Confirmar estado real con `git status --short --branch` y `git worktree list`; si no hay worktree tactico abierto, elegir el siguiente paquete seguro por trazabilidad. |
| Siguiente accion | Confirmar estado real con `git status --short --branch` y `git worktree list`; si no hay worktree tactico abierto, elegir el siguiente paquete seguro por trazabilidad. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
