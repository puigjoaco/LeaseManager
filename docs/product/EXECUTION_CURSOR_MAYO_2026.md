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
| Frente activo | Sin paquete tactico abierto tras cerrar Reporting Etapa 7: resumen anual exige obligaciones trazables no vacias. |
| Fuente exacta | `main` limpio tras mergear PR #788 (`e4b79eff`); rescue queda pausado fuera de alcance. |
| Brecha activa | Ninguna para el paquete cerrado: `_assert_annual_tax_traceability()` ya exige `fiscal_year` trazable y `obligaciones` como lista no vacia, alineado con `audit_stage7_reporting_readiness`. |
| Motivo de prioridad | Evitar que una reanudacion o compactacion reabra el paquete ya mergeado y permitir elegir el siguiente frente seguro desde el estado real del repo. |
| Worktree | Ninguno de producto activo; este cursor se cierra desde `D:/Proyectos/LeaseManager-stage7-annual-summary-obligations-cursor`. |
| Rama | `codex/stage7-annual-summary-obligations-cursor` solo para cierre de cursor. |
| Estado | Cierre de cursor en curso. |
| Gate esperado | Validacion documental minima: `git status --short --branch`, `git diff --check`, `scripts/assert-repo-hygiene.ps1 -IncludeUntracked` y CI GitHub antes de merge. |
| Estado al cerrar paquete | PR #788 mergeado en `main` con `e4b79eff`. Validado con focal Reporting anual (2 tests OK), suite Reporting/readiness Etapa 7 (64 tests OK), `manage.py check`, migraciones dry-run, gate Etapa 7 local parcial esperado, `npm ci`, `npm run build`, `npm run lint`, acceptance local (`ACCEPTANCE_EXIT=0`, 1336 tests OK), higiene, `git diff --check` y CI GitHub. |
| Bloqueos relacionados | Etapa 7 sigue parcial para cierre evidencial: requiere fuente `snapshot_controlado` o `real_autorizado`, evidencias Stage 5/6, prueba API/backoffice y responsables no sensibles. Este paquete solo endurece rutas locales de Reporting. |
| Politica de reanudacion | Si se reanuda con este cursor ya mergeado, no rehacer PR #788 ni redactar de nuevo el goal. Confirmar estado real del repo y seleccionar el siguiente frente seguro desbloqueado por trazabilidad. El rescue pausado no habilita lectura de datos reales ni bloquea trabajo local seguro. |
| Siguiente accion | Tras mergear este cierre de cursor, sincronizar `main`, limpiar el worktree `codex/stage7-annual-summary-obligations-cursor` y diagnosticar el siguiente frente seguro desde PRD/stage cards/trazabilidad. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
