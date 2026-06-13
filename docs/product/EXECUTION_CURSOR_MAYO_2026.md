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
| Frente activo | Sin paquete tactico abierto tras preparar PR #795: API tributaria anual usa codigos de configuracion fiscal alineados con readiness. |
| Fuente exacta | PR #795 preparado desde `main` limpio `e8e8247c`; commit de paquete `3934fec`. Rescue queda pausado fuera de alcance. |
| Brecha activa | Ninguna tras preparar PR #795: `_assert_annual_tax_traceability()` separa falta de `ConfiguracionFiscalEmpresa` para proceso anual, DDJJ y F22, en correspondencia con `audit_stage7_reporting_readiness`. |
| Motivo de prioridad | Mantener un punto de reanudacion estable que no reabra paquetes ya mergeados ni transforme contexto auxiliar en trabajo nuevo. |
| Worktree | Ninguno de producto activo tras preparar PR #795. |
| Rama | `main` tras mergear PR #795. |
| Estado | Listo para seleccionar el siguiente frente seguro tras mergear PR #795. |
| Gate esperado | Antes de abrir un nuevo paquete: leer este cursor, confirmar `git status --short --branch` y `git worktree list`, diagnosticar PRD/stage cards/trazabilidad, y abrir worktree `codex/...` si el cambio no es trivial. |
| Estado al cerrar paquete | PR #795 preparado con focal Reporting anual (4 tests OK), suite Reporting/readiness Etapa 7 (74 tests OK), `manage.py check`, migraciones dry-run, gate Etapa 7 local parcial esperado, `npm ci`, `npm run build`, `npm run lint`, acceptance local (`ACCEPTANCE_EXIT=0`, 1346 tests OK), higiene y `git diff --check`. |
| Bloqueos relacionados | Etapa 7 sigue parcial para cierre evidencial: requiere fuente `snapshot_controlado` o `real_autorizado`, evidencias Stage 5/6, prueba API/backoffice y responsables no sensibles. Este paquete solo endurece rutas locales de Reporting. |
| Politica de reanudacion | No rehacer PR #795 ni redactar de nuevo el goal. Confirmar estado real del repo y seleccionar el siguiente frente seguro desbloqueado por trazabilidad. El rescue pausado no habilita lectura de datos reales ni bloquea trabajo local seguro. |
| Siguiente accion | Tras mergear PR #795 y sincronizar `main`, diagnosticar el siguiente frente seguro desde PRD/stage cards/trazabilidad y abrir un paquete pequeno, verificable y trazable. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
