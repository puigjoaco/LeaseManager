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
| Frente activo | `stage6-post-objective-proof`. |
| Fuente exacta | `main` posterior al paquete `stage6-objective-proof-evidence`; evidencia local controlada bajo `local-evidence/` ignorada por Git. |
| Brecha activa | La prueba espejo AC2024/AT2025 quedo documentada como confirmada en modo controlado. No reabrir ownership, bienes raices, DDJJ esperadas ni comparador para esta prueba salvo evidencia nueva contradictoria. |
| Motivo de prioridad | Evitar que reanudaciones conviertan el paquete de evidencia ya cerrado en una nueva tarea. El siguiente avance debe partir de que LeaseManager ya probo la arquitectura espejo desde insumos contables/libros AC2024 hacia artefactos AT2025 comparables, usando outputs finales solo como comparacion read-only. |
| Worktree | No hay worktree tactico activo esperado para este frente. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `main`; abrir un nuevo worktree `codex/...` solo para el siguiente cambio no trivial. |
| Estado | La evidencia local controlada queda bajo `local-evidence/inmobiliaria-puig/ac2024-at2025-real-estate-ownership-20260617/` e ignorada por Git. El paquete combinado conserva 12 meses, ownership validado y 6 bienes raices. `audit_annual_tax_controlled_package_readiness --fail-on-blocking` queda listo para writer/generacion. `apply_annual_tax_controlled_db_load --apply --fail-on-blocking` carga 12 meses, ownership y 6 bienes raices. `run_annual_tax_controlled_mirror --apply --fail-on-blocking` con las 12 DDJJ esperadas queda `ready_for_generation=true`. `compare_annual_tax_expected_outputs` queda sin blockers. `scripts/run-stage6-mirror-proof-gate.ps1 -FailOnIncomplete` queda `classification=resuelto_confirmado`, `ready_for_architecture_proof=true`, `ready_for_objective_completion=true`, sin blockers. |
| Gate esperado | Este paquete documenta el cierre de la prueba espejo objetivo AC2024/AT2025. No declara renta final presentada, no abre SII real y no sustituye revision tributaria responsable para produccion. |
| Estado al cerrar paquete | No reabrir prompts de goal, ownership, labor source ref, bienes raices, DDJJ esperadas, DDJJ/F22 semantico ni comparador Balance/RLI/CPT/RAI/SAC para esta prueba espejo salvo evidencia nueva contradictoria. |
| Bloqueos relacionados | No quedan blockers del proof objetivo AC2024/AT2025. Los cierres productivos futuros siguen sujetos a responsable tributario, autorizacion explicita, fuentes reales/controladas vigentes y gates externos cuando corresponda. |
| Politica de reanudacion | No usar `.env`, secretos, DB real, produccion, SII real, EDIG ejecutable ni integraciones externas sin autorizacion explicita. Las salidas F22/DDJJ/Balance/RLI/CPT/RAI/SAC esperadas son comparacion externa read-only, nunca input de calculo. |
| Siguiente accion | Continuar el proyecto desde el siguiente frente real de producto/arquitectura, partiendo de que la arquitectura espejo AC2024/AT2025 ya quedo probada en modo controlado. No crear tareas de goal prompt ni repetir el cierre de este proof. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
