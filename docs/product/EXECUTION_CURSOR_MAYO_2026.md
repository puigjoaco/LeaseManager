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
| Frente activo | `main-clean-next-traceable-front`. |
| Fuente exacta | `main` posterior al cierre del gate espejo backend, wrapper Stage 6 mirror proof, corrida controlada AC2024 y boundary laboral-previsional DJ1887. |
| Brecha activa | No hay paquete tactico abierto para AC2024/AT2025. El comando Django, el wrapper operativo del gate espejo y el boundary `labor_previsional_source` quedan como caminos canonicos para futuras corridas controladas o autorizadas. |
| Motivo de prioridad | Evitar reabrir paquetes cerrados y mantener la siguiente decision basada en el estado real del repo, trazabilidad y cursor. |
| Worktree | Ningun worktree tactico de AC2024/AT2025 debe quedar activo despues de mergear el paquete vigente. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `main` limpio despues de cerrar el paquete. Para el proximo paquete no trivial abrir worktree hermano `codex/...` desde `main`. |
| Estado | El gate espejo AC2024/AT2025 distingue fuente documentada, arquitectura espejo, comparacion lista, readiness Etapa 6, seguridad y revision pendiente. La corrida controlada real desde fuente externa AC2024 ya confirma writer DB listo, 12 `MonthlyTaxFact`, 10 F29/obligaciones y generacion anual preliminar con source bundle, workbooks, registros, matriz, dossier, export, DDJJ y F22 preparados en SQLite local ignorada. DJ1887 aceptada ahora exige fuente laboral-previsional revisable: falta de `payroll_support` bloquea el source bundle, y paquetes con `labor_previsional.required=true` requieren `labor_previsional.source_ref` no sensible. |
| Gate esperado | Para AC2024/AT2025 controlado o autorizado, usar `scripts/run-stage6-mirror-proof-gate.ps1`; con `-FailOnIncomplete` solo si se exige `ready_for_objective_completion=true`. El siguiente frente util de esta linea es completar snapshot controlado de ownership/bienes raices, revisar artefactos anuales o elegir otro paquete trazable desde `main` limpio. |
| Estado al cerrar paquete | No reabrir prompts de goal, boundary contable de PR #859, gate espejo backend, wrapper Stage 6, corrida controlada AC2024, boundary laboral-previsional DJ1887, selector anual, ownership, respaldo tributario, bienes raices, DDJJ/F22 semantico, Balance General, RLI/CPT/RAI/SAC ni EDIG como bloqueo general salvo bug nuevo. |
| Bloqueos relacionados | Sin autorizacion o fuente real no se debe presentar SII, declarar calculo tributario final ni afirmar cierre productivo. El bloqueo externo queda como condicion de cierre real/productivo, no como freno para seguir por el siguiente frente seguro. |
| Politica de reanudacion | No reabrir goal prompts, EDIG ni paquetes mergeados. No usar `.env`, secretos, DB real, produccion, SII real ni integraciones externas sin autorizacion explicita. Si falta fuente externa, continuar con preparacion local segura y trazable. |
| Siguiente accion | Continuar con el siguiente paquete trazable desde `main` limpio. Si sigue la linea AC2024/AT2025, transformar fuente societaria/propiedades suficiente en snapshot controlado de ownership/bienes raices, revisar artefactos anuales o registrar explicitamente decision manual si no existe fuente suficiente. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
