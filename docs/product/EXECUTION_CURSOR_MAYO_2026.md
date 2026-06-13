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
| Frente activo | Etapa 5 Contabilidad: guard de vigencias solapadas en reglas contables activas. |
| Fuente exacta | `main` limpio en `cc3e742c` tras PR #769; rescue queda pausado fuera de alcance. |
| Brecha activa | `ReglaContable` podia conservar reglas activas solapadas para la misma empresa, tipo de evento y version de plan, dejando que el servicio eligiera una por orden en vez de exigir vigencia unica. |
| Motivo de prioridad | Evitar ambiguedad de mapping contable antes de contabilizar eventos y dejar readiness explicita para snapshots heredados. |
| Worktree | `D:/Proyectos/LeaseManager-stage5-rule-window-guard`. |
| Rama | `codex/stage5-rule-window-guard`. |
| Estado | Validado localmente; listo para commit, PR, CI, merge y limpieza. |
| Gate esperado | Focal Contabilidad/readiness, suite impactada Etapa 5, `manage.py check`, migraciones dry-run, gate local Etapa 5 parcial esperado, frontend build/lint, acceptance, higiene y `git diff --check`. |
| Estado al cerrar paquete | Local: focal 2 tests OK; suite impactada Contabilidad/Etapa 5/Reporting 104 tests OK; `manage.py check` OK; migraciones dry-run OK; gate Etapa 5 `classification=parcial`, `ready_for_stage5_contabilidad=false`; `npm ci` 0 vulnerabilidades; build/lint OK; acceptance local 1317 tests OK; higiene repo y `git diff --check` OK. |
| Bloqueos relacionados | Etapa 5 sigue parcial para cierre evidencial: requiere Conciliacion cerrada y fuente `snapshot_controlado` o `real_autorizado` con evidencia ledger/reportes/responsables. Este paquete solo endurece reglas locales sin fuente real/controlada. |
| Politica de reanudacion | Si se reanuda con este worktree abierto, continuar este paquete hasta PR/CI/merge/limpieza antes de abrir otro frente. El rescue pausado no habilita lectura de datos reales ni bloquea trabajo local seguro. |
| Siguiente accion | Commit, PR, esperar CI, mergear en `main`, limpiar worktree/rama y dejar cursor sin paquete abierto. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
