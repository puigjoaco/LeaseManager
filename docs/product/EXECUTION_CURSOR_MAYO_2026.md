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
| Frente activo | Sin paquete tactico abierto tras preparar PR #797: API tributaria anual bloquea DDJJ/F22 con capacidad SII de otra familia. |
| Fuente exacta | PR #797 preparado desde `main` limpio `e71b5226`; commit de paquete `8270962`. Rescue queda pausado fuera de alcance. |
| Brecha activa | Ninguna tras preparar PR #797: `_assert_annual_tax_traceability()` bloquea DDJJ/F22 heredados con `capacidad_tributaria.capacidad_key` cruzada usando codigos equivalentes a readiness. |
| Motivo de prioridad | Mantener la API de Reporting anual alineada con readiness y dominio SII sin usar secretos, SII real, snapshots, DB historicas ni datos reales. |
| Worktree | Ninguno de producto activo tras preparar PR #797. |
| Rama | `main` tras mergear PR #797. |
| Estado | Listo para seleccionar el siguiente frente seguro tras mergear PR #797. |
| Gate esperado | Antes de abrir un nuevo paquete: leer este cursor, confirmar `git status --short --branch` y `git worktree list`, diagnosticar PRD/stage cards/trazabilidad, y abrir worktree `codex/...` si el cambio no es trivial. |
| Estado al cerrar paquete | PR #797 preparado con focal Reporting anual (3 tests OK), suite Reporting/readiness Etapa 7 (77 tests OK), `manage.py check`, migraciones dry-run, gate Etapa 7 local parcial esperado, `npm ci`, `npm run build`, `npm run lint`, acceptance local (`ACCEPTANCE_EXIT=0`, 1349 tests OK), higiene, `git diff --check` y CI remoto GitHub en verde. |
| Bloqueos relacionados | Etapa 7 sigue parcial para cierre evidencial: requiere fuente `snapshot_controlado` o `real_autorizado`, evidencias Stage 5/6, prueba API/backoffice y responsables no sensibles. Este paquete solo endurece rutas locales de Reporting. |
| Politica de reanudacion | No rehacer PR #797 ni redactar de nuevo el goal. Confirmar estado real del repo y seleccionar el siguiente frente seguro desbloqueado por trazabilidad. El rescue pausado no habilita lectura de datos reales ni bloquea trabajo local seguro. |
| Siguiente accion | Tras mergear PR #797 y sincronizar `main`, diagnosticar el siguiente frente seguro desde PRD/stage cards/trazabilidad y abrir un paquete pequeno, verificable y trazable. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
