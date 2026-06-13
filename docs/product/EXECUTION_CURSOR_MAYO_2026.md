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
| Frente activo | Etapa 7 Reporting: cubrir en API el bloqueo de procesos anuales sin estado trazable. |
| Fuente exacta | `main` limpio `76cc663e` tras mergear PR #800. Rescue queda pausado fuera de alcance. |
| Brecha activa | La API tributaria anual ya bloquea `ProcesoRentaAnual` en estado no trazable con `reporting.annual_process_not_traceable`, pero faltaba test focal del endpoint alineado con `stage7.reporting.annual_process_not_traceable`. |
| Motivo de prioridad | Fortalecer evidencia API/readiness de Reporting tributario anual antes de seguir con cierres finales o pruebas externas. |
| Worktree | `D:/Proyectos/LeaseManager-stage7-annual-process-state-api`. |
| Rama | `codex/stage7-annual-process-state-api`. |
| Estado | Validacion local completa; paquete listo para commit, PR y CI remoto. |
| Gate esperado | Test focal de resumen tributario anual, suite Reporting/readiness Etapa 7, `manage.py check`, migraciones dry-run, gate Etapa 7 local parcial esperado, frontend build/lint, acceptance local, higiene y CI remoto antes de merge. |
| Estado al cerrar paquete | Pendiente de commit, PR, CI remoto, merge y limpieza. Validacion local: focal 2 tests OK, suite Reporting/readiness 85 tests OK, `manage.py check` OK, migraciones dry-run OK, gate Etapa 7 local parcial esperado, `npm ci`, build/lint frontend, acceptance local 1357 tests OK. |
| Bloqueos relacionados | Etapa 7 sigue parcial para cierre evidencial: requiere fuente `snapshot_controlado` o `real_autorizado`, evidencias Stage 5/6, prueba API/backoffice y responsables no sensibles. Este paquete solo alinea rutas locales de Reporting. |
| Politica de reanudacion | Continuar este worktree hasta PR, CI, merge y limpieza. No rehacer PR #800 ni redactar de nuevo el goal. El rescue pausado no habilita lectura de datos reales ni bloquea trabajo local seguro. |
| Siguiente accion | Ejecutar higiene final, commitear, abrir PR y esperar CI remoto. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
