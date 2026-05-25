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
| Frente activo | Ninguno. Ultimo paquete cerrado: Etapa 7 - Reporting tributario anual exige ano comercial consistente. |
| Fuente exacta | PR #268; commit `a136f37`; merge `45b7628`. `docs/product/STAGE_CARDS/ETAPA_7_REPORTING_TRAZABILIDAD.md`; `docs/product/TRACEABILITY_MATRIX_MAYO_2026.md`; `backend/reporting/services.py`; `backend/core/stage7_reporting_readiness.py`; tests Reporting y readiness Etapa 7. |
| Brecha activa | Ninguna abierta en cursor. La brecha de reportes tributarios anuales con `fiscal_year` de proceso/DDJJ/F22 desalineado contra `anio_tributario` quedo corregida y validada en PR #268. |
| Motivo de prioridad | Paquete cerrado porque alineo Reporting con la regla de Renta Anual ya reforzada: el reporte tributario anual no puede construirse ni pasar readiness si sus origenes declaran un ano comercial distinto del inmediatamente anterior al ano tributario. No requirio `.env`, secretos, DB historica, datos reales, certificados ni integraciones SII externas. |
| Worktree | Ninguno tactico abierto. |
| Rama | Ninguna tactica abierta. |
| Estado | PR #268 mergeado, CI `acceptance` en verde, main sincronizado y worktree tactico eliminado. |
| Gate esperado | Etapa 7 sigue como diagnostico parcial/no evidencial; no cierra sin fuente autorizada, cierres/snapshot controlado, datos autorizados y trazabilidad final. |
| Estado al cerrar paquete | Cerrado en main con merge `45b7628`; siguiente frente debe elegirse por trazabilidad desde estado limpio. |
| Bloqueos relacionados | Fuente `snapshot_controlado` o `real_autorizado`, cierres/snapshot controlado, datos autorizados y trazabilidad final siguen siendo condicion de cierre real, no de preparacion local. |
| Politica de reanudacion | Confirmar estado real con `git status --short --branch` y `git worktree list`; si no hay worktree tactico abierto, elegir el siguiente paquete seguro por trazabilidad. |
| Siguiente accion | Confirmar estado real con `git status --short --branch` y `git worktree list`; si no hay worktree tactico abierto, elegir el siguiente paquete seguro por trazabilidad. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
