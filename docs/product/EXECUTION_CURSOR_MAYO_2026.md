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
| Frente activo | Sin paquete tactico abierto tras preparar PR #803: API tributaria anual cubre refs F22 finales del proceso. |
| Fuente exacta | `main` limpio `91f77974` tras mergear PR #802. Rescue queda pausado fuera de alcance. |
| Brecha activa | Ninguna tras preparar PR #803: la API tributaria anual tiene cobertura focal para `reporting.annual_process_f22_ref_missing` y `reporting.annual_process_f22_ref_sensitive`, sin exponer valores sensibles. |
| Motivo de prioridad | Completar evidencia API/readiness de Reporting tributario anual para referencias finales de ProcesoRentaAnual, sin depender de SII real ni fuente autorizada. |
| Worktree | `D:/Proyectos/LeaseManager-stage7-annual-process-f22-ref-api`. |
| Rama | `codex/stage7-annual-process-f22-ref-api`. |
| Estado | PR #803 preparado y CI remoto en verde; pendiente merge y limpieza. |
| Gate esperado | Tests focales de resumen tributario anual para `annual_process_f22_ref_missing` y `annual_process_f22_ref_sensitive`, suite Reporting/readiness Etapa 7, `manage.py check`, migraciones dry-run, gate Etapa 7 local parcial esperado, frontend build/lint, acceptance local, higiene y CI remoto antes de merge. |
| Estado al cerrar paquete | PR #803 preparado con focal Reporting anual (5 tests OK), suite Reporting/readiness Etapa 7 (89 tests OK), `manage.py check`, migraciones dry-run, gate Etapa 7 local parcial esperado, `npm ci`, `npm run build`, `npm run lint`, acceptance local (`ACCEPTANCE_EXIT=0`, 1361 tests OK), higiene, `git diff --check` y CI remoto GitHub en verde. |
| Bloqueos relacionados | Etapa 7 sigue parcial para cierre evidencial: requiere fuente `snapshot_controlado` o `real_autorizado`, evidencias Stage 5/6, prueba API/backoffice y responsables no sensibles. Este paquete solo alinea rutas locales de Reporting anual. |
| Politica de reanudacion | No rehacer PR #803 ni redactar de nuevo el goal. Tras mergear y sincronizar `main`, seleccionar el siguiente frente seguro desbloqueado por trazabilidad. El rescue pausado no habilita lectura de datos reales ni bloquea trabajo local seguro. |
| Siguiente accion | Mergear PR #803, sincronizar `main`, limpiar worktree/rama y diagnosticar el siguiente frente seguro. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
