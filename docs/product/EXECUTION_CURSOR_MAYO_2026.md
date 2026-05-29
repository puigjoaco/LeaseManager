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
| Frente activo | Etapa 5 / Contabilidad / liquidaciones mensuales trazables. |
| Fuente exacta | `01_Set_Vigente/PRD_CANONICO.md` lineas 310, 433, 445 y 446; `docs/product/STAGE_CARDS/ETAPA_5_CIERRE_MENSUAL_CONTABILIDAD.md`; trazabilidad y evidencia vigentes. |
| Brecha activa | No existe entidad canonica de liquidacion mensual ni linea explicita de comision/honorario de administracion; el cierre Etapa 5 no puede verificar que liquidaciones y saldo final queden trazables. |
| Motivo de prioridad | Completa una brecha local de Contabilidad/Etapa 5 sin secretos, datos reales ni integraciones externas; prepara el cierre contable para liquidaciones explicadas. |
| Worktree | `D:/Proyectos/LeaseManager-stage5-monthly-liquidations`. |
| Rama | `codex/stage5-monthly-liquidations`. |
| Estado | Implementacion y validacion local completadas; pendiente commit, PR, CI, merge y limpieza. |
| Gate esperado | Tests focales Contabilidad/API/readiness; suite impactada `contabilidad`, `core.tests_stage5_contabilidad_readiness`, `reporting`; `manage.py check`; `makemigrations --check --dry-run`; readiness Etapa 5 local; frontend build/lint; acceptance local; higiene repo y `git diff --check`. |
| Estado al cerrar paquete | Validacion local OK: focal 6 tests, suite impactada 96 tests, `manage.py check`, `makemigrations --check --dry-run`, gate Etapa 5 local parcial esperado, `npm ci`, `npm run build`, `npm run lint`, acceptance local 1092 tests, higiene repo y `git diff --check`. |
| Bloqueos relacionados | Sin bloqueo externo nuevo; Etapa 5 no se declara cerrada sin Conciliacion cerrada y fuente `snapshot_controlado` o `real_autorizado`. |
| Politica de reanudacion | Si se reanuda con un worktree sucio, terminar o pausar ese paquete antes de abrir otro frente. |
| Siguiente accion | Diagnosticar el siguiente frente seguro desde el estado real del repo. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
