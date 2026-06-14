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
| Frente activo | Ninguno abierto. Ultimo paquete: `stage6-annual-trial-balance`. |
| Fuente exacta | `main` en `37f279d7`, posterior al merge de PR #839. |
| Brecha cerrada localmente | Etapa 6 incorpora una capa anual de balance de 8 columnas trazable entre `BalanceComprobacion` y RLI/CPT/DJ1847, sin declarar calculo tributario final. |
| Motivo de prioridad | La matriz oficial AT2026 indicaba unir contabilidad y renta mediante DJ1847/balance/RLI/CPT con fuente oficial/experta, no por inferencia directa desde metricas mensuales ni IA autonoma. |
| Worktree | Cerrable tras merge: `D:/Proyectos/LeaseManager-stage6-annual-trial-balance`. |
| Rama | Cerrable tras merge: `codex/stage6-annual-trial-balance`. |
| Estado | Paquete validado localmente y listo para commit, PR, CI, merge y limpieza. |
| Gate esperado | `scripts/run-stage6-readiness-gate.ps1` queda en `classification=parcial`; no cierra Etapa 6 sin snapshot/control autorizado, fuente oficial/experta final, responsable y evidencia no sensible. |
| Estado al cerrar paquete | Despues del merge, main debe quedar limpio y sin worktree tactico; reanudar desde repo real y elegir siguiente brecha segura por trazabilidad. |
| Bloqueos relacionados | Presentacion F22/DDJJ final sigue bloqueada sin formato/certificacion SII vigente, responsable, autorizacion explicita y evidencia no sensible. Reglas tributarias finales, contribuciones y mapping fiscal definitivo requieren fuente oficial/experta. |
| Politica de reanudacion | No reabrir este frente si ya esta mergeado; tomar el siguiente frente seguro desde trazabilidad, sin goal prompts ni EDIG salvo nueva razon concreta. |
| Siguiente accion | Commit, PR, CI, merge y limpieza de `stage6-annual-trial-balance`; luego continuar por el siguiente paquete seguro sin usar secretos, datos reales ni SII real. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
