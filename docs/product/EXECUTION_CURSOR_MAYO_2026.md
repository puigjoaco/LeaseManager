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
| Frente activo | Etapa 1 - Contratos: politica documentada para base de renovacion con tramos. |
| Fuente exacta | `01_Set_Vigente/PRD_CANONICO.md`; `backend/contratos/models.py`; `backend/contratos/serializers.py`; `backend/core/stage1_matrix_audit.py`; `backend/contratos/tests.py`; `backend/core/tests_stage1_matrix_audit.py`; `docs/product/TRACEABILITY_MATRIX_MAYO_2026.md`; `docs/product/EVIDENCE_REGISTER_MAYO_2026.md`. |
| Brecha activa | El PRD exige que si un contrato con tramos se renueva, la base por defecto sea el ultimo tramo vigente salvo politica documentada distinta; el modelo actual no fuerza ni audita esa documentacion. |
| Motivo de prioridad | Es la siguiente regla local de Contratos posterior a avisos, renovaciones ejecutadas y contratos retroactivos. |
| Worktree | `D:/Proyectos/LeaseManager-stage1-renewal-base-policy`. |
| Rama | `codex/stage1-renewal-base-policy`. |
| Estado | En implementacion local. |
| Gate esperado | Etapa 1 debe seguir como diagnostico parcial/no evidencial; este paquete endurece preparacion local y no cierra sin fuente `snapshot_controlado` o `real_autorizado`. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Fuente `snapshot_controlado` o `real_autorizado` sigue siendo condicion de cierre real de Etapa 1, no de preparacion local. |
| Politica de reanudacion | Confirmar estado real con `git status --short --branch` y `git worktree list`; si no hay worktree tactico abierto, elegir el siguiente paquete seguro por trazabilidad. |
| Siguiente accion | Implementar guard y auditor para renovaciones automaticas con base distinta al ultimo tramo sin politica no sensible, validar con pruebas proporcionales, actualizar evidencia/trazabilidad y cerrar con PR, CI, merge y limpieza. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
