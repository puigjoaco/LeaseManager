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
| Frente activo | Etapa 6/7: exigir responsable de revision no sensible en auditoria anual `status_updated`. |
| Fuente exacta | `main` limpio `56b13d08` tras mergear PR #805. Rescue queda pausado fuera de alcance. |
| Brecha activa | ProcesoRentaAnual, DDJJ y F22 avanzados ya exigen `responsable_revision_ref`, pero los eventos auditables `sii.ddjj_preparacion.status_updated` y `sii.f22_preparacion.status_updated` aun no son bloqueantes si omiten responsable de revision o conservan una referencia sensible. |
| Motivo de prioridad | Cerrar la trazabilidad del boundary contable-tributario asistido: un dossier anual puede estar preparado/aprobado internamente solo si la mutacion y la auditoria prueban responsable revisor sin secretos. |
| Worktree | `D:/Proyectos/10_ACTIVOS/LeaseManager-stage6-review-audit`. |
| Rama | `codex/stage6-review-audit`. |
| Estado | Validado localmente; PR/CI/merge pendiente. |
| Gate esperado | Readiness Etapa 6/7, API reporting anual, auditoria SII anual, tests focales e impactados; `manage.py check`, migraciones dry-run, gates locales parciales esperados, frontend build/lint si aplica, acceptance local, higiene, CI remoto antes de merge. |
| Estado al cerrar paquete | Pendiente de PR, CI, merge y limpieza. |
| Bloqueos relacionados | Etapas 6 y 7 siguen sin cierre real sin fuente `snapshot_controlado` o `real_autorizado`, evidencia Stage 5/4, regla fiscal, certificados, SII/ledger autorizados y responsable final. Este paquete solo endurece preparacion segura y trazabilidad local. |
| Politica de reanudacion | No reabrir PR #805 ni reescribir goal. Si esta rama ya aparece mergeada, elegir el siguiente frente seguro desde trazabilidad. |
| Siguiente accion | Abrir PR, esperar CI, mergear y limpiar worktree tactico. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
