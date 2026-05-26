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
| Frente activo | Etapa 1 / Contratos - cambio de arrendatario mediante termino y contrato nuevo. |
| Fuente exacta | `01_Set_Vigente/PRD_CANONICO.md` lineas 98, 355 y escenario transversal 4; `docs/AUDITORIA_PRODUCTO_ARQUITECTURA_MAYO_2026.md` escenario 4 parcial. |
| Brecha activa | Falta flujo operacional atomico y auditable para crear aviso de termino y contrato futuro con nuevo arrendatario, sin reescribir identidad historica. |
| Motivo de prioridad | Brecha local trazable de Etapa 1 que no requiere secretos, datos reales ni integraciones externas. |
| Worktree | `D:/Proyectos/LeaseManager-stage1-tenant-replacement`. |
| Rama | `codex/stage1-tenant-replacement`. |
| Estado | Paquete tactico abierto. |
| Gate esperado | Tests focales Contratos + auditor Etapa 1, suite impactada, `manage.py check`, migraciones dry-run, readiness Etapa 1 local, frontend build, acceptance si el impacto lo justifica. |
| Estado al cerrar paquete | PR #296 mergeado en `main` con merge `c3c3b5d`; CI `acceptance` pass; worktree tactico y rama remota eliminados. |
| Bloqueos relacionados | Fuente `snapshot_controlado` o `real_autorizado` sigue siendo condicion de cierre real de Etapa 1, no de preparacion local. |
| Politica de reanudacion | Confirmar estado real con `git status --short --branch` y `git worktree list`; si no hay worktree tactico abierto, elegir el siguiente paquete seguro por trazabilidad. |
| Siguiente accion | Implementar flujo guiado de cambio de arrendatario, validarlo, actualizar trazabilidad/evidencia y cerrar con PR/CI/merge/limpieza. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
