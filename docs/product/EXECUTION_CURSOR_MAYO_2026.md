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
| Frente activo | Etapa 6: exigir responsable de revision no sensible en artefactos anuales avanzados. |
| Fuente exacta | `main` limpio `887c3a4d` tras mergear PR #804. Rescue queda pausado fuera de alcance. |
| Brecha activa | El boundary asistido ya esta en PRD/arquitectura, pero ProcesoRentaAnual, DDJJ y F22 avanzados aun no conservan una referencia propia de responsable de revision. |
| Motivo de prioridad | Convertir el boundary contable-tributario asistido en enforcement local: un dossier anual no debe tratarse como aprobado/observado/rectificado sin responsable trazable no sensible. |
| Worktree | `D:/Proyectos/LeaseManager-stage6-review-responsible`. |
| Rama | `codex/stage6-review-responsible`. |
| Estado | Validado localmente; PR/CI/merge pendiente. Si este paquete ya aparece mergeado en `main`, no reabrirlo. |
| Gate esperado | Migracion/modelo/API/readiness/tests Etapa 6 y reporting impactado; `manage.py check`, migraciones dry-run, gate Etapa 6 local parcial esperado, frontend build/lint si aplica, acceptance local, higiene, CI remoto antes de merge. |
| Estado al cerrar paquete | Pendiente de PR/CI/merge. |
| Bloqueos relacionados | Etapa 6 sigue sin cierre real sin fuente `snapshot_controlado` o `real_autorizado`, evidencia Stage 5/4, regla fiscal, certificados y responsable final. Este paquete solo agrega responsable de revision a artefactos anuales avanzados. |
| Politica de reanudacion | No reabrir PR #804 ni reescribir goal. Continuar este paquete solo si la rama `codex/stage6-review-responsible` sigue abierta; si ya fue mergeada, elegir el siguiente frente seguro desde trazabilidad. |
| Siguiente accion | Abrir PR, esperar CI, mergear y limpiar worktree. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
