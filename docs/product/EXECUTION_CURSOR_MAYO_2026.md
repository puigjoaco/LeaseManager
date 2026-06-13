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
| Frente activo | Etapa 6/7: backoffice SII captura y muestra responsable de revision anual. |
| Fuente exacta | `main` limpio `f821a111` tras mergear PR #806. Rescue queda pausado fuera de alcance. |
| Brecha activa | Backend/API/readiness ya exigen `responsable_revision_ref` para DDJJ/F22 avanzados, pero el backoffice SII aun no permite registrar revision anual con responsable/ref/observacion y Reporting anual no expone el responsable redactado en su payload. |
| Motivo de prioridad | Completar el flujo operativo del boundary asistido: el usuario debe poder preparar y revisar DDJJ/F22 desde backoffice dejando responsable trazado, sin automatizar presentacion final ni usar SII real. |
| Worktree | `D:/Proyectos/10_ACTIVOS/LeaseManager-stage6-annual-review-ui`. |
| Rama | `codex/stage6-annual-review-ui`. |
| Estado | Validado localmente; PR, CI, merge y limpieza pendientes. |
| Gate esperado | UI SII/Reporting, API reporting anual, tests focales, `manage.py check`, migraciones dry-run, frontend build/lint, acceptance local, higiene, CI remoto antes de merge. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Etapas 6 y 7 siguen sin cierre real sin fuente `snapshot_controlado` o `real_autorizado`, evidencia Stage 5/4, regla fiscal, certificados, SII/ledger autorizados y responsable final. Este paquete solo habilita preparacion/revision local trazable. |
| Politica de reanudacion | No reabrir PR #806 ni reescribir goal. Si esta rama ya aparece mergeada, elegir el siguiente frente seguro desde trazabilidad. |
| Siguiente accion | Abrir PR, esperar CI, mergear y limpiar. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
