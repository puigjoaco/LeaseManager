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
| Frente activo | Sin paquete tactico activo; PR #807 cerrado. |
| Fuente exacta | `main` limpio y sincronizado despues de PR #807 y de este cursor post-merge. Rescue queda pausado fuera de alcance. |
| Brecha activa | Pendiente de seleccionar desde trazabilidad y estado real del repo. No reabrir el paquete Etapa 6/7 de responsable anual en backoffice. |
| Motivo de prioridad | Evitar que reanudaciones o compactaciones repitan el paquete cerrado; el siguiente avance debe salir del repo actual, no del chat viejo ni de un PR ya mergeado. |
| Worktree | Ninguno activo para producto; solo root principal. |
| Rama | `main`. |
| Estado | Main limpio y sincronizado tras PR #807 y cursor post-merge. |
| Gate esperado | Antes del proximo cambio no trivial: leer este cursor, confirmar `git status --short --branch` y `git worktree list`, elegir brecha segura desde trazabilidad, abrir worktree `codex/...`, validar proporcionalmente y cerrar con PR/CI/merge/limpieza. |
| Estado al cerrar paquete | PR #807 mergeado, CI remoto OK, rama local/remota y worktree tactico eliminados. |
| Bloqueos relacionados | Etapas 6 y 7 siguen sin cierre real sin fuente `snapshot_controlado` o `real_autorizado`, evidencia Stage 5/4, regla fiscal, certificados, SII/ledger autorizados y responsable final. Los bloqueos son condiciones de cierre, no freno para seguir preparando frentes locales seguros. |
| Politica de reanudacion | No reabrir PR #806 ni PR #807, no reescribir goal, no repetir prompts de goal. Si no hay worktree tactico sucio, diagnosticar el siguiente frente seguro desde trazabilidad/documentos vigentes. |
| Siguiente accion | Diagnosticar el siguiente frente seguro y verificable desde `main` limpio; abrir worktree tactico solo si el cambio no es trivial. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
