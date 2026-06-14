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
| Frente activo | Sin paquete tactico abierto. |
| Fuente exacta | `main` en `e85f0235`, posterior al merge de PR #838 (`stage6-annual-review-checklist`). |
| Brecha activa | Ninguna en cursor. `stage6-annual-review-checklist` quedo integrado: `AnnualTaxReviewChecklist` separa preparacion mecanica de decision tributaria supervisada. |
| Motivo de prioridad | Evitar que reanudaciones reabran el paquete cerrado o vuelvan a discutir goal prompts; el siguiente avance debe nacer del estado real del repo y la trazabilidad vigente. |
| Worktree | Solo root principal activo; el worktree tactico `D:/Proyectos/LeaseManager-stage6-annual-review-checklist` fue eliminado. |
| Rama | `main` tras merge; rama tactica local/remota eliminada. |
| Estado | Paquete #838 cerrado, CI remoto verde, mergeado y limpieza hecha. |
| Gate esperado | Mantener `classification=parcial`; no cerrar presentacion anual sin fuente autorizada, formato/certificacion SII vigente, validacion fiscal/oficial, responsable y evidencia no sensible. |
| Estado al cerrar paquete | `stage6-annual-review-checklist` cerrado. El paquete anual preparado queda conectado a checklist de revision responsable no sensible, con readiness bloqueante si falta, esta incompleto o intenta aprobar sin responsable/evidencia. |
| Bloqueos relacionados | Presentacion F22/DDJJ final sigue bloqueada sin formato/certificacion SII vigente, responsable, autorizacion explicita y evidencia no sensible. Reglas tributarias finales, contribuciones y mapping RLI/CPT/DJ/F22 requieren fuente oficial/experta. |
| Politica de reanudacion | No reabrir EDIG ni goal prompts. Si no hay worktree sucio, continuar por el siguiente frente util que no requiera datos reales, secretos, presentacion SII ni decision tributaria final autonoma. |
| Siguiente accion | Desde `main` limpio, elegir el siguiente frente util y seguro segun arquitectura, trazabilidad y stage cards, sin usar secretos, datos reales, SII real ni decision tributaria final autonoma. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
