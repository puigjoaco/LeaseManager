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
| Frente activo | Sin paquete tactico activo; escoger siguiente frente seguro desde `main`. |
| Fuente exacta | `main` posterior a PR #834 (`stage6-official-source-retrieved-date`) y a esta actualizacion de cursor. |
| Brecha activa | Ninguna brecha abierta por cursor. El paquete `stage6-official-source-retrieved-date` quedo cerrado: `AnnualTaxOfficialSource.retrieved_on` no puede ser futuro para fuentes revisadas/aprobadas y el bootstrap demo anual usa fecha local de corrida. |
| Motivo de prioridad | Evitar que una reanudacion o compactacion reabra el PR #834 ya cerrado como si todavia faltaran PR, CI o merge. |
| Worktree | Solo debe quedar el worktree principal de `main`; eliminar worktrees tacticos cerrados. |
| Rama | `main` tras merge. |
| Estado | PR #834 mergeado en `main`; validacion local y CI remoto pasaron. No repetir este paquete. |
| Gate esperado | Mantener `classification=parcial`; no cerrar presentacion anual sin fuente autorizada, formato/certificacion SII vigente, validacion fiscal/oficial, responsable y evidencia no sensible. |
| Estado al cerrar paquete | `stage6-official-source-retrieved-date` cerrado. Las fuentes AT revisadas/aprobadas no aceptan fecha de recuperacion futura y el demo anual queda temporalmente consistente sin usar fuente real. |
| Bloqueos relacionados | Presentacion F22/DDJJ final sigue bloqueada sin formato/certificacion SII vigente, responsable, autorizacion explicita y evidencia no sensible. Reglas tributarias finales, contribuciones y mapping RLI/CPT/DJ/F22 requieren fuente oficial/experta. |
| Politica de reanudacion | No reabrir EDIG ni goal prompts. Si no hay worktree sucio, continuar por el siguiente frente util que no requiera datos reales, secretos, presentacion SII ni decision tributaria final autonoma. |
| Siguiente accion | Confirmar `main` limpio y escoger el siguiente frente Stage 6/7 no sensible segun trazabilidad vigente. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
