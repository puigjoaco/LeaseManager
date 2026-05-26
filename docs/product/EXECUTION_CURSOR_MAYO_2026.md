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
| Frente activo | Etapa 1 / Patrimonio. |
| Fuente exacta | `01_Set_Vigente/PRD_CANONICO.md` reglas de sucesion, transferencia y redistribucion de participaciones patrimoniales; `docs/product/STAGE_CARDS/ETAPA_1_DATOS_REALES.md`; trazabilidad vigente. |
| Brecha activa | Falta flujo operacional auditado para transferir, reemplazar o redistribuir una participacion activa conservando el 100% del owner. |
| Motivo de prioridad | Es un frente temprano de Patrimonio, localmente verificable, no requiere secretos, datos reales ni integraciones externas, y evita ediciones manuales sin traza sobre participaciones. |
| Worktree | `D:/Proyectos/LeaseManager-stage1-participation-transfer`. |
| Rama | `codex/stage1-participation-transfer`. |
| Estado | Paquete implementado y validado localmente; pendiente de PR/CI/merge. |
| Gate esperado | Tests focales de Patrimonio y auditor Etapa 1; suite impactada Patrimonio + `core.tests_stage1_matrix_audit`; `manage.py check`; `makemigrations --check --dry-run`; readiness local Etapa 1; frontend build; acceptance local; CI GitHub. |
| Estado al cerrar paquete | Validacion local completa OK: focal Patrimonio/auditor, suite impactada 149 tests, `manage.py check`, `makemigrations --check --dry-run`, readiness local Etapa 1, `npm ci`, `npm run build` y acceptance local 801 tests. Pendiente CI remoto y merge. |
| Bloqueos relacionados | Fuente `snapshot_controlado` o `real_autorizado` sigue siendo condicion de cierre real de Etapa 1, no de preparacion local. |
| Politica de reanudacion | Confirmar estado real con `git status --short --branch` y `git worktree list`; si no hay worktree tactico abierto, elegir el siguiente paquete seguro por trazabilidad. |
| Siguiente accion | Implementar flujo auditado de transferencia de participaciones, actualizar stage card/trazabilidad/evidencia, validar y cerrar por PR/CI/merge/limpieza. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
