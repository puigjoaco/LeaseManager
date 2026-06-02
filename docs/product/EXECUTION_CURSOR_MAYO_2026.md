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
| Frente activo | Etapa 5 Contabilidad - vinculo exacto liquidacion/cierre aprobado. |
| Fuente exacta | Estado real de `main` en `1dd11f8` despues de PR #631, stage cards, trazabilidad, evidencia y bloqueos vigentes. |
| Brecha activa | `audit_stage5_contabilidad_readiness` debe exigir que la `LiquidacionMensual` de empresa preparada/aprobada pertenezca al mismo `CierreMensualContable` aprobado, no solo al mismo periodo. |
| Motivo de prioridad | El servicio `approve_monthly_close()` ya exige ese vinculo exacto; readiness debe detectar snapshots heredados que conserven una liquidacion de periodo desanclada del cierre. |
| Worktree | `D:/Proyectos/LeaseManager-stage5-liquidation-close-link`. |
| Rama | `codex/stage5-liquidation-close-link`. |
| Estado | Paquete tactico abierto para corregir readiness, test focal, trazabilidad y evidencia. |
| Gate esperado | Test focal de readiness Etapa 5, suite impactada Contabilidad/Stage5, `manage.py check`, migraciones dry-run, gate local Etapa 5, frontend build/lint si aplica, acceptance local, higiene, `git diff --check` y CI antes de merge. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Los cierres evidenciales que dependan de fuentes externas siguen condicionados por autorizacion/fuente controlada y no bloquean trabajo local seguro. |
| Politica de reanudacion | Si no hay worktree tactico abierto, diagnosticar desde `main` limpio y elegir el siguiente frente util por orden de construccion, trazabilidad, stage cards y evidencia vigente. |
| Siguiente accion | Confirmar `git status --short --branch` y `git worktree list`; luego elegir el siguiente paquete pequeno, local, verificable y cerrable. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
