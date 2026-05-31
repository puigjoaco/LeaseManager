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
| Frente activo | Compliance datos sensibles / trazabilidad de preparacion de exportaciones desde servicio. |
| Fuente exacta | Estado real de `main` en `f1ed310`, `docs/product/STAGE_CARDS/ETAPA_0_GOBIERNO_BASELINE.md`, trazabilidad, evidencia y bloqueos vigentes. |
| Brecha activa | `prepare_sensitive_export()` puede ser llamado internamente con `motivo` vacio o sin `created_by`, aunque la API exige motivo y readiness clasifica exportaciones sin actor. |
| Motivo de prioridad | Es una brecha local verificable del frente no cerrado mas bajo: evita que llamadas internas controladas creen exportaciones sensibles sin motivo operativo o actor creador trazable. |
| Worktree | `D:/Proyectos/LeaseManager-compliance-prepare-traceability`. |
| Rama | `codex/compliance-prepare-traceability`. |
| Estado | Validado local; pendiente PR, CI, merge y limpieza. |
| Gate esperado | Focal Compliance/readiness, suite Compliance/readiness, `manage.py check`, migraciones dry-run, gate local Compliance, frontend build/lint si aplica, acceptance local, higiene repo y `git diff --check`. |
| Estado al cerrar paquete | Focal Compliance/readiness 3 tests OK; suite Compliance/readiness 99 tests OK; `manage.py check` OK; `makemigrations --check --dry-run --noinput` sin cambios; gate Compliance local `classification=parcial`, `ready_for_compliance_data=false`; `npm ci` 0 vulnerabilidades; `npm run build` OK; `npm run lint` OK; acceptance local 1121 tests OK; `scripts/assert-repo-hygiene.ps1` OK; `git diff --check` OK; pendiente PR, CI, merge y limpieza. |
| Bloqueos relacionados | BLK-010 sigue abierto para cierre legal-operativo de Compliance; este paquete no requiere `.env`, secretos, DB historica, datos reales, snapshots autorizados, backfills, deploys ni integraciones externas. |
| Politica de reanudacion | Si este worktree aparece sucio, terminar este paquete o pausarlo explicitamente antes de abrir otro frente. |
| Siguiente accion | Abrir PR, esperar CI, mergear y limpiar worktree tactico. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
