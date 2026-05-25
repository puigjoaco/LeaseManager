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
| Frente activo | Etapa 1 / Operacion - evidencia operativa de cuenta recaudadora activa. |
| Fuente exacta | `01_Set_Vigente/PRD_CANONICO.md` lineas 167-169; `docs/product/TRACEABILITY_MATRIX_MAYO_2026.md`; `docs/product/STAGE_CARDS/ETAPA_1_DATOS_REALES.md`. |
| Brecha activa | `CuentaRecaudadora` activa valida owner y dependencias, pero no exige modo operativo/gate manual controlado ni evidencia trazable no sensible. |
| Motivo de prioridad | PRD exige que una cuenta activa no baste por existir en tabla: debe declarar uso operativo, gate bancario o modo manual controlado y evidencia de conciliabilidad. |
| Worktree | `D:/Proyectos/LeaseManager-stage1-account-operational-evidence`. |
| Rama | `codex/stage1-account-operational-evidence`. |
| Estado | Paquete tactico abierto para endurecer cuentas activas y cubrir API/auditor/evidencia. |
| Gate esperado | Los gates externos siguen siendo condiciones de cierre real, no de preparacion local. |
| Estado al cerrar paquete | PR #290 mergeado en `main` con merge `f491ad4`; CI `acceptance` pass; worktree tactico y rama remota eliminados. |
| Bloqueos relacionados | Fuente `snapshot_controlado` o `real_autorizado` sigue siendo condicion de cierre real de Etapa 1, no de preparacion local. |
| Politica de reanudacion | Confirmar estado real con `git status --short --branch` y `git worktree list`; si no hay worktree tactico abierto, elegir el siguiente paquete seguro por trazabilidad. |
| Siguiente accion | Implementar paquete acotado, validar proporcionalmente y cerrar con PR, CI, merge y limpieza. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
