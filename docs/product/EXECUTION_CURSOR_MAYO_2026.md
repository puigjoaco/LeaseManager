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
| Frente activo | Etapa 7 Reporting: cubrir en API refs F22 finales del proceso anual. |
| Fuente exacta | `main` limpio `91f77974` tras mergear PR #802. Rescue queda pausado fuera de alcance. |
| Brecha activa | La API ya bloquea `reporting.annual_process_f22_ref_missing` y `reporting.annual_process_f22_ref_sensitive`, pero esos codigos no tenian pruebas focales del endpoint tributario anual. |
| Motivo de prioridad | Completar evidencia API/readiness de Reporting tributario anual para referencias finales de ProcesoRentaAnual, sin depender de SII real ni fuente autorizada. |
| Worktree | `D:/Proyectos/LeaseManager-stage7-annual-process-f22-ref-api`. |
| Rama | `codex/stage7-annual-process-f22-ref-api`. |
| Estado | Validacion local completa; paquete listo para commit, PR y CI remoto. |
| Gate esperado | Tests focales de resumen tributario anual para `annual_process_f22_ref_missing` y `annual_process_f22_ref_sensitive`, suite Reporting/readiness Etapa 7, `manage.py check`, migraciones dry-run, gate Etapa 7 local parcial esperado, frontend build/lint, acceptance local, higiene y CI remoto antes de merge. |
| Estado al cerrar paquete | Pendiente de commit, PR, CI remoto, merge y limpieza. Validacion local: focal 5 tests OK, suite Reporting/readiness 89 tests OK, `manage.py check` OK, migraciones dry-run OK, gate Etapa 7 local parcial esperado, `npm ci`, build/lint frontend, acceptance local 1361 tests OK. |
| Bloqueos relacionados | Etapa 7 sigue parcial para cierre evidencial: requiere fuente `snapshot_controlado` o `real_autorizado`, evidencias Stage 5/6, prueba API/backoffice y responsables no sensibles. Este paquete solo alinea rutas locales de Reporting anual. |
| Politica de reanudacion | Continuar este worktree hasta PR, CI, merge y limpieza. No redactar de nuevo el goal. El rescue pausado no habilita lectura de datos reales ni bloquea trabajo local seguro. |
| Siguiente accion | Ejecutar higiene final, commitear, abrir PR y esperar CI remoto. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
