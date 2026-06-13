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
| Frente activo | Reporting Etapa 7 - referencias finales DDJJ/F22 con texto operativo en API tributaria anual. |
| Fuente exacta | `main` limpio tras mergear PR #779 (`b9974dbc`); rescue queda pausado fuera de alcance. |
| Brecha activa | `_assert_annual_tax_traceability()` ya bloquea refs finales faltantes, pero en DDJJ/F22 usaba truthiness simple; snapshots heredados con `paquete_ref` o `borrador_ref` solo espacios podian pasar la API aunque readiness ya los marca faltantes. |
| Motivo de prioridad | Alinear API y readiness antes de reportar tributario anual como verificado sobre refs finales sin texto real. |
| Worktree | `D:/Proyectos/LeaseManager-stage7-annual-final-ref-text-api`. |
| Rama | `codex/stage7-annual-final-ref-text-api`. |
| Estado | En implementacion local segura. |
| Gate esperado | Focal API anual, suite Reporting/readiness, `manage.py check`, migraciones dry-run, gate Etapa 7 local parcial, frontend build/lint, acceptance local, higiene y CI GitHub. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Etapa 7 sigue parcial para cierre evidencial: requiere fuente `snapshot_controlado` o `real_autorizado`, evidencias Stage 5/6, prueba API/backoffice y responsables no sensibles. Este paquete solo endurece rutas locales de Reporting sin leer datos reales ni integraciones externas. |
| Politica de reanudacion | Si este worktree queda abierto, continuar este paquete antes de abrir otro frente. El rescue pausado no habilita lectura de datos reales ni bloquea trabajo local seguro. |
| Siguiente accion | Implementar `_has_text()` para refs finales DDJJ/F22, cubrir API con tests de dato heredado por `update()`, validar y cerrar con PR/CI/merge/limpieza. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
