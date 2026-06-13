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
| Frente activo | Paquete tactico abierto: API tributaria anual bloquea DDJJ/F22 con capacidad SII de otra familia. |
| Fuente exacta | `main` limpio sincronizado en `e71b5226` tras mergear PR #796. Rescue queda pausado fuera de alcance. |
| Brecha activa | `_assert_annual_tax_traceability()` no bloqueaba DDJJ/F22 heredados con `capacidad_tributaria.capacidad_key` cruzada, mientras `audit_stage7_reporting_readiness` si los clasificaba como `stage7.reporting.annual_ddjj_invalid` / `stage7.reporting.annual_f22_invalid`. |
| Motivo de prioridad | Alinear API de Reporting anual con readiness y dominio SII sin usar secretos, SII real, snapshots, DB historicas ni datos reales. |
| Worktree | `D:/Proyectos/LeaseManager-stage7-annual-capability-codes`. |
| Rama | `codex/stage7-annual-capability-codes`. |
| Estado | En implementacion local: servicio Reporting, tests de API, stage card, trazabilidad, evidencia y cursor. |
| Gate esperado | Focal Reporting anual, suite Reporting/readiness Etapa 7, `manage.py check`, migraciones dry-run, gate Etapa 7 local parcial esperado, frontend build/lint, acceptance local, higiene, PR, CI, merge y limpieza. |
| Estado al cerrar paquete | Pendiente hasta validar, abrir PR, pasar CI, mergear a `main` y remover el worktree tactico. |
| Bloqueos relacionados | Etapa 7 sigue parcial para cierre evidencial: requiere fuente `snapshot_controlado` o `real_autorizado`, evidencias Stage 5/6, prueba API/backoffice y responsables no sensibles. Este paquete solo endurece rutas locales de Reporting. |
| Politica de reanudacion | No rehacer PR #796 ni redactar de nuevo el goal. Continuar este paquete desde el worktree tactico hasta cierre o pausa explicita. El rescue pausado no habilita lectura de datos reales ni bloquea trabajo local seguro. |
| Siguiente accion | Ejecutar tests focales, corregir si falla, validar suite impactada y cerrar paquete con PR/CI/merge/limpieza. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
