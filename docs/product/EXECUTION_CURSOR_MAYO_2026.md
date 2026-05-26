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
| Frente activo | Etapa 5 / Contabilidad - reverso o asiento complementario posterior al cierre. |
| Fuente exacta | `01_Set_Vigente/PRD_CANONICO.md` lineas 245, 283, 376 y 608; `docs/AUDITORIA_PRODUCTO_ARQUITECTURA_MAYO_2026.md`; `docs/product/STAGE_CARDS/ETAPA_5_CIERRE_MENSUAL_CONTABILIDAD.md`; `docs/product/TRACEABILITY_MATRIX_MAYO_2026.md`. |
| Brecha activa | La politica y reapertura existen, pero falta flujo final que deje efecto contable trazable al reabrir un cierre aprobado segun politica de reverso/asiento complementario. |
| Motivo de prioridad | Brecha local, segura y explicitamente trazada en Contabilidad; no requiere secretos, `.env`, DB historica, datos reales, banco ni SII. |
| Worktree | `D:/Proyectos/LeaseManager-stage5-reopen-accounting-effect`. |
| Rama | `codex/stage5-reopen-accounting-effect`. |
| Estado | Paquete tactico abierto; mantener `main` limpio. |
| Gate esperado | Etapa 5 debe seguir como `parcial` si faltan dependencias externas, pero el flujo de reapertura debe quedar probado localmente. |
| Estado al cerrar paquete | PR #292 mergeado en `main` con merge `f84f115`; CI `acceptance` pass; worktree tactico y rama remota eliminados. |
| Bloqueos relacionados | Fuente `snapshot_controlado` o `real_autorizado` sigue siendo condicion de cierre real de Etapa 1, no de preparacion local. |
| Politica de reanudacion | Confirmar estado real con `git status --short --branch` y `git worktree list`; si no hay worktree tactico abierto, elegir el siguiente paquete seguro por trazabilidad. |
| Siguiente accion | Elegir siguiente paquete seguro por trazabilidad, abrir worktree `codex/...` si es no trivial, validar proporcionalmente y cerrar con PR/CI/merge/limpieza. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
