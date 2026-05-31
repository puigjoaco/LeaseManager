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
| Frente activo | Etapa 3 / Conciliacion / Django admin / redaccion de conexion bancaria en movimientos importados. |
| Fuente exacta | Estado real de `main` en `ecbf116`, PRD canonico, `docs/product/STAGE_CARDS/ETAPA_3_BANCO_CONCILIACION.md`, trazabilidad, evidencia y bloqueos vigentes. |
| Brecha activa | `MovimientoBancarioImportadoAdmin` todavia exponia la relacion cruda `conexion_bancaria` en `fields` y `list_display`; la ficha Etapa 3 exige labels/versiones redactadas en superficies admin de movimientos. |
| Motivo de prioridad | Es un cierre local, pequeno y verificable de superficie admin sensible; no requiere banco real, `.env`, secretos, DB historica, snapshot autorizado, backfill, deploy ni integracion externa. |
| Worktree | `D:/Proyectos/LeaseManager-stage3-movement-connection-admin-redaction`. |
| Rama | `codex/stage3-movement-connection-admin-redaction`. |
| Estado | Implementado y validado localmente; pendiente commit, PR, CI, merge y limpieza. |
| Gate esperado | Gate local Etapa 3 diagnostico: `classification=parcial`, `ready_for_stage3_conciliacion=false`; no declara cierre de etapa. |
| Estado al cerrar paquete | Focal 1 test OK, suite impactada 142 tests OK, `manage.py check`, migraciones dry-run, readiness local Etapa 3 `classification=parcial`, `npm ci`, `npm run build`, `npm run lint`, acceptance local 1115 tests OK, higiene repo y `git diff --check`. |
| Bloqueos relacionados | Sin bloqueo externo nuevo. El cierre real de Etapa 3 sigue dependiendo de banco real o snapshot autorizado con referencias no sensibles. |
| Politica de reanudacion | Si este worktree aparece sucio, terminar o pausar este paquete antes de abrir otro frente. |
| Siguiente accion | Cerrar paquete con commit, PR, CI, merge y limpieza. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
