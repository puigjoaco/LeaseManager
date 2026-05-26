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
| Frente activo | Etapa 1 / Contratos - renovacion automatica operacional por `PeriodoContractual`. |
| Fuente exacta | `01_Set_Vigente/PRD_CANONICO.md` regla `AvisoTermino` bloquea renovacion automatica; `docs/AUDITORIA_PRODUCTO_ARQUITECTURA_MAYO_2026.md` escenario PRD 3 parcial; `docs/product/STAGE_CARDS/ETAPA_1_DATOS_REALES.md` renovaciones con tramos. |
| Brecha activa | Los periodos y reglas de base existen, pero falta flujo operativo/API que ejecute una renovacion automatica trazable y bloqueada por aviso registrado. |
| Motivo de prioridad | Es la brecha local mas baja y explicita de Contratos que no requiere secretos, `.env`, datos reales ni integraciones externas. |
| Worktree | `D:/Proyectos/LeaseManager-stage1-contract-auto-renewal`. |
| Rama | `codex/stage1-contract-auto-renewal`. |
| Estado | Paquete tactico abierto; mantener `main` limpio. |
| Gate esperado | Diagnostico local Etapa 1 como preparacion segura, sin declarar cierre real sin fuente autorizada. |
| Estado al cerrar paquete | PR #294 mergeado en `main` con merge `d6541be`; CI `acceptance` pass; worktree tactico y rama remota eliminados. |
| Bloqueos relacionados | Fuente `snapshot_controlado` o `real_autorizado` sigue siendo condicion de cierre real de Etapa 1, no de preparacion local. |
| Politica de reanudacion | Confirmar estado real con `git status --short --branch` y `git worktree list`; si no hay worktree tactico abierto, elegir el siguiente paquete seguro por trazabilidad. |
| Siguiente accion | Implementar renovacion automatica operacional, validar tests/gate proporcionales, cerrar con PR/CI/merge/limpieza y resetear cursor. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
