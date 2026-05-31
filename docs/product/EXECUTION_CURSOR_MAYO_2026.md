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
| Frente activo | Etapa 3 / Conciliacion / supersesion de resoluciones manuales. |
| Fuente exacta | Estado real de `main` en `049009c` despues de PR #599, stage cards, trazabilidad, evidencia y bloqueos vigentes. |
| Brecha activa | `supersede_manual_resolutions_for_movement()` no declara frontera transaccional propia aunque cambia `ManualResolution` y crea auditoria `audit.manual_resolution.superseded`; una llamada directa podria dejar supersesion sin evento si falla la auditoria. |
| Motivo de prioridad | La stage card de Etapa 3 exige que resoluciones manuales obsoletas queden `superseded` con motivo, metadata y evento de auditoria alineado; readiness ya detecta fallas heredadas, pero el servicio debe impedirlas de origen. |
| Worktree | `D:/Proyectos/LeaseManager-stage3-manual-resolution-supersede-atomicity`. |
| Rama | `codex/stage3-manual-resolution-supersede-atomicity`. |
| Estado | Paquete tactico implementado y validado localmente; pendiente PR, CI remoto, merge y limpieza. |
| Gate esperado | Etapa 3 local debe seguir `classification=parcial`, `ready_for_stage3_conciliacion=false`; el paquete mejora preparacion segura, no cierra etapa. |
| Estado al cerrar paquete | Implementa `@transaction.atomic` en `supersede_manual_resolutions_for_movement()`, prueba rollback ante fallo de `audit.manual_resolution.superseded`, actualiza stage card, trazabilidad y evidencia. Validacion local: focal 4 tests OK; impactada Conciliacion/Stage 3 110 tests OK; `manage.py check` OK; `makemigrations --check --dry-run --noinput` OK; gate Etapa 3 local `classification=parcial`, `ready_for_stage3_conciliacion=false`; `npm ci`, `npm run build`, `npm run lint` OK; acceptance local 1134 tests OK. |
| Bloqueos relacionados | Etapa 3 sigue parcial para cierre real por banco real o snapshot autorizado, evidencia Etapa 2 y prueba bancaria controlada. Este paquete no debe usar `.env`, secretos, DB historica, datos reales, snapshots autorizados, backfills, deploys ni integraciones externas. |
| Politica de reanudacion | Si este worktree existe, continuar este paquete hasta PR/CI/merge/limpieza antes de abrir otro frente; si aparece sucio, terminar o pausar aqui de forma explicita. |
| Siguiente accion | Ejecutar higiene final, crear PR, esperar CI, mergear, sincronizar `main`, cerrar cursor y limpiar worktree tactico. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
