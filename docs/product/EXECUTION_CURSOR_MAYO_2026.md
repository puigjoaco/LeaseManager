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
| Frente activo | Sin paquete tactico abierto posterior a integrar este paquete. |
| Fuente exacta | Estado real de `main` tras integrar PR #590 en `c2a584b`, `docs/product/STAGE_CARDS/ETAPA_5_CIERRE_MENSUAL_CONTABILIDAD.md`, trazabilidad, evidencia y bloqueos vigentes. |
| Brecha activa | Ninguna. Ultimo paquete cerrado: `approve_monthly_close()` exige `LiquidacionMensual` de empresa preparada para el mismo cierre/periodo antes de aprobar un cierre mensual contable. |
| Motivo de prioridad | El paquete cerro una brecha local verificable de Etapa 5: alinear servicio operacional, readiness de liquidaciones y bootstraps demo sin usar fuentes externas. |
| Worktree | Ninguno tras merge. El laboratorio usado por este paquete fue `D:/Proyectos/LeaseManager-stage5-close-liquidation-guard`. |
| Rama | `main` limpio tras merge; laboratorio cerrado: `codex/stage5-close-liquidation-guard`. |
| Estado | Paquete Contabilidad / Etapa 5 cerrado; luego de este ajuste de cursor, queda libre para diagnosticar el siguiente frente seguro. |
| Gate esperado | No aplica a paquete cerrado. El siguiente paquete debe definir gates proporcionales antes de editar. |
| Estado al cerrar paquete | Focal Contabilidad 3 tests OK; suite impactada Contabilidad/Stage5 69 tests OK; `manage.py check` OK; `makemigrations --check --dry-run --noinput` sin cambios; readiness local Etapa 5 `classification=parcial`, `ready_for_stage5_contabilidad=false`; `npm run build`, `npm run lint` OK; acceptance local 1125 tests OK; higiene repo y `git diff --check` OK; CI GitHub acceptance OK; PR #590 mergeado en `c2a584b`; worktree tactico y rama local/remota eliminados. |
| Bloqueos relacionados | Etapa 5 sigue parcial para cierre real por Conciliacion/fuente autorizada/evidencia externa. Este paquete no requiere `.env`, secretos, DB historica, datos reales, snapshots autorizados, backfills, deploys ni integraciones externas. |
| Politica de reanudacion | Si `git status` y `git worktree list` muestran solo `main` limpio, diagnosticar el siguiente frente seguro; si aparece un worktree sucio, terminar o pausar ese paquete antes de abrir otro frente. |
| Siguiente accion | Diagnosticar el siguiente frente seguro desde el estado real del repo. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
