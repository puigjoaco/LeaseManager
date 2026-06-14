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
| Frente activo | Ninguno; `stage6-trial-balance-mapping-guard` cerrado por este paquete. |
| Fuente exacta | Base `main` en `2c9de1d`, posterior al merge de PR #845. |
| Brecha activa | Cerrada localmente: Etapa 6 bloquea mappings basados en `annual_trial_balance.*` sin `trial_balance_classifier` DJ1847 o apuntando directo a destinos posteriores como F22/DDJJ. |
| Motivo de prioridad | Impedir que la union contabilidad -> renta salte desde balance anual directo a F22/DDJJ sin pasar por RLI/CPT trazable. |
| Worktree | `D:/Proyectos/LeaseManager-stage6-trial-balance-mapping-guard` hasta merge; luego remover. |
| Rama | `codex/stage6-trial-balance-mapping-guard` hasta merge; luego eliminar local/remoto. |
| Estado | Implementacion local finalizada; pendiente commit, PR, CI, merge y limpieza. |
| Gate esperado | `scripts/run-stage6-readiness-gate.ps1` queda en `classification=parcial`; no cierra Etapa 6 ni presenta DDJJ/F22 sin fuente final, certificacion/formato, responsable, autorizacion y evidencia no sensible. |
| Estado al cerrar paquete | Commit, PR, CI, merge y limpieza; main debe quedar sincronizado y sin worktree tactico de este frente. |
| Bloqueos relacionados | Mapping fiscal final sigue bloqueado sin fuente DJ1847/F22 revisada, responsable tributario, casos controlados, autorizacion explicita y evidencia no sensible. |
| Politica de reanudacion | No reabrir goal prompts, EDIG ni este frente; si el paquete ya esta mergeado, diagnosticar el siguiente frente seguro desde main limpio y fuentes rectoras. |
| Siguiente accion | Cerrar el paquete por PR/CI/merge. Despues del merge, continuar solo con el siguiente frente seguro; no usar SII real, navegador, datos reales ni secretos sin autorizacion explicita. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
