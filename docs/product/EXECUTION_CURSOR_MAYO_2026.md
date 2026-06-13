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
| Frente activo | Etapa 7 Reporting: cubrir en API el bloqueo de eventos contables sin origen trazable. |
| Fuente exacta | `main` limpio `f88e4c86` tras mergear PR #799. Rescue queda pausado fuera de alcance. |
| Brecha activa | La API financiera mensual ya bloquea eventos sin `entidad_origen_tipo` o `entidad_origen_id` con `reporting.event_origin_missing`, pero faltaba test focal del endpoint para ese guard alineado con `stage7.reporting.event_origin_missing`. |
| Motivo de prioridad | Fortalecer evidencia API/readiness de Reporting financiero antes de seguir con cierres finales o pruebas externas. |
| Worktree | `D:/Proyectos/LeaseManager-stage7-financial-event-origin-api`. |
| Rama | `codex/stage7-financial-event-origin-api`. |
| Estado | Validacion local completa; listo para commit, PR y CI. |
| Gate esperado | Test focal de resumen financiero, suite Reporting/readiness Etapa 7, `manage.py check`, migraciones dry-run, gate Etapa 7 local parcial esperado, frontend build/lint, acceptance local, higiene y CI remoto antes de merge. |
| Estado al cerrar paquete | Pendiente de PR/CI/merge. Validacion local: focal Reporting financiero (2 tests OK), suite Reporting/readiness Etapa 7 (84 tests OK), `manage.py check`, migraciones dry-run, gate Etapa 7 local parcial esperado, `npm ci`, `npm run build`, `npm run lint`, acceptance local (`ACCEPTANCE_EXIT=0`, 1356 tests OK), higiene y `git diff --check`. |
| Bloqueos relacionados | Etapa 7 sigue parcial para cierre evidencial: requiere fuente `snapshot_controlado` o `real_autorizado`, evidencias Stage 5/6, prueba API/backoffice y responsables no sensibles. Este paquete solo alinea rutas locales de Reporting. |
| Politica de reanudacion | Continuar este worktree hasta PR, CI, merge y limpieza. No rehacer PR #799 ni redactar de nuevo el goal. El rescue pausado no habilita lectura de datos reales ni bloquea trabajo local seguro. |
| Siguiente accion | Commit, PR, CI remoto, merge y limpieza. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
