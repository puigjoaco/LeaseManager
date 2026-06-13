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
| Frente activo | Etapa 7 Reporting: API tributaria anual alineada con estado trazable de DDJJ/F22. |
| Fuente exacta | `main` limpio tras PR #777 (`7881eb9c`); worktree tactico `D:/Proyectos/LeaseManager-stage7-annual-document-state-api`. |
| Brecha activa | `_assert_annual_tax_traceability()` validaba el estado trazable del proceso anual, pero aun podia entregar reporte con DDJJ/F22 en estado preliminar si conservaban resumen; readiness Etapa 7 ya bloqueaba esas condiciones. |
| Motivo de prioridad | Evitar reporte tributario anual con trazabilidad API mas debil que el gate de Reporting y la stage card. |
| Worktree | `D:/Proyectos/LeaseManager-stage7-annual-document-state-api`. |
| Rama | `codex/stage7-annual-document-state-api`. |
| Estado | Validacion local pre-PR completa; pendiente commit, PR, CI, merge y limpieza. |
| Gate esperado | Focal Reporting anual, suite impactada `reporting core.tests_stage7_reporting_readiness`, `manage.py check`, migraciones dry-run, gate Etapa 7 local parcial, frontend build/lint, acceptance local, higiene repo y `git diff --check`. |
| Estado al cerrar paquete | Pre-PR local OK: focal Reporting anual 3 tests, suite impactada Reporting/readiness 55 tests, `manage.py check`, migraciones dry-run, gate Etapa 7 parcial, `npm ci`, build/lint, acceptance local 1327 tests, higiene repo y `git diff --check`. |
| Bloqueos relacionados | Etapa 7 sigue parcial para cierre evidencial: requiere fuente `snapshot_controlado` o `real_autorizado`, evidencias Stage 5/6, prueba API/backoffice y responsables no sensibles. Este paquete solo endurece rutas locales sin leer datos reales ni integraciones externas. |
| Politica de reanudacion | Continuar este worktree hasta cerrar PR o pausar explicitamente; no reabrir paquetes Reporting ya cerrados ni metatareas de goal. El rescue pausado no habilita lectura de datos reales ni bloquea trabajo local seguro. |
| Siguiente accion | Completar validaciones proporcionales, actualizar evidencia/trazabilidad, abrir PR, esperar CI, mergear y limpiar worktree. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
