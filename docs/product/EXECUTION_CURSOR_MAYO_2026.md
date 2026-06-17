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
  explicita en este cursor o descartar con instruccion segura antes de abrir un frente
  distinto.
- Solo el estado real del repo y este cursor definen la siguiente accion
  operativa.
- El contexto auxiliar no autoriza secretos, no abre gates y no crea tareas
  nuevas salvo solicitud textual actual del usuario.
- Si este cursor nombra una rama/worktree ya cerrados y `main` contiene el
  merge correspondiente, no recrear el paquete anterior: tratarlo como cerrado,
  corregir este cursor y continuar con el siguiente frente seguro.

## Cursor actual

| Campo | Valor |
| --- | --- |
| Frente activo | `codex/stage6-official-compatibility-matrix`. |
| Fuente exacta | `main` en `3458be43`, despues del merge confirmado de PR #904 `codex/cursor-terminology-after-verifier`. |
| Brecha activa | Etapa 6 ya genera y verifica paquete local DDJJ/F22. Falta consolidar una matriz propia, testeable y documentada de compatibilidad oficial SII AT2026 para separar archivo/certificacion/upload/portal de cualquier API asumida, presentacion real o calculo final. |
| Motivo de prioridad | El objetivo pide avanzar desde artefactos comparables hacia salidas revisables/certificables. Antes de producir formatos oficiales, LeaseManager debe registrar que fuentes SII vigentes respaldan cada camino y que limites siguen bloqueados. |
| Worktree | `D:/Proyectos/10_ACTIVOS/LeaseManager-stage6-official-compatibility-matrix`. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `codex/stage6-official-compatibility-matrix`. |
| Estado | Paquete en curso solo mientras esta rama/worktree exista. Validaciones locales completas antes del rebase a `origin/main`; faltan resolver cierre documental post-rebase, higiene/diff-check, commit, PR, CI, merge y limpieza. |
| Gate esperado | Este paquete no declara cierre de Etapa 6, no genera archivo oficial SII, no presenta renta y no confirma API. Solo baja fuentes SII AT2026 a una matriz local validable que mantiene `official_submission_allowed=false` y `final_tax_calculation=false`. |
| Estado al cerrar paquete | Si `main` contiene el merge de este frente y la rama/worktree ya no existe, no reabrirlo ni repetir PR/CI/merge. Buscar el siguiente frente seguro desde repo limpio. |
| Bloqueos relacionados | Formato/certificacion F22, DDJJ y presentacion SII siguen bloqueados por formato/certificacion vigente aplicable, responsable tributario, autorizacion explicita y evidencia no sensible. |
| Politica de reanudacion | No usar `.env`, secretos, DB real, produccion, SII real, EDIG ejecutable ni integraciones externas sin autorizacion explicita. Las salidas F22/DDJJ/Balance/RLI/CPT/RAI/SAC esperadas son comparacion externa read-only, nunca input de calculo. |
| Siguiente accion | Completar matriz oficial AT2026, tests, docs/evidencia y cierre por PR/CI/merge/limpieza si pasa. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
