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
| Frente activo | `stage6-mirror-proof-evidence-bridge`. |
| Fuente exacta | worktree `D:/Proyectos/10_ACTIVOS/LeaseManager-stage6-mirror-proof-evidence-bridge`, sobre `main` `38ef6bc8`. |
| Brecha activa | El checklist de ownership ya esta integrado y el patch ownership controlado existe bajo `local-evidence/`, pero el proof agregado seguia leyendo solo el manifiesto historico. Eso reabria `ownership_source_missing` y `expected_output_value_equality_completion` aunque la evidencia posterior ya estaba lista. |
| Motivo de prioridad | Es el gate que responde directamente al objetivo AC2024/AT2025: confirmar si LeaseManager puede partir desde contabilidad/libros cerrados y llegar a artefactos comparables con los finales sin usar outputs esperados como input. El gate debe reflejar el estado real: source/arquitectura/comparacion OK y no falsos bloqueos por manifiesto antiguo. |
| Worktree | Continuar/cerrar `D:/Proyectos/10_ACTIVOS/LeaseManager-stage6-mirror-proof-evidence-bridge`. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `codex/stage6-mirror-proof-evidence-bridge`; al cerrar, PR/CI/merge y limpiar worktree. |
| Estado | Focal `core.tests_annual_tax_mirror_proof` pasa. Corrida real local con `scripts/run-stage6-mirror-proof-gate.ps1 -OwnershipEvidencePath <ownership_patch_controlled_validation.json>` sobre SQLite controlada AC2024/AT2025 queda `classification=parcial`, `source_documentation_confirmed=true`, `ownership_evidence_confirmed=true`, `architecture_complete_for_mirror_run=true`, `comparison_ready_for_mirror_conclusion=true` y unico blocker `stage6.real_estate_item_missing`. |
| Gate esperado | Este paquete no cierra Etapa 6 ni renta final: corrige el proof para que no repita bloqueos ya resueltos. El cierre objetivo sigue pendiente hasta despejar bienes raices y pasar el gate completo con evidencia. |
| Estado al cerrar paquete | No reabrir ownership, labor source ref, DDJJ/F22 semantico, comparador Balance/RLI/CPT/RAI/SAC ni prompts de goal. El siguiente frente real debe atacar `stage6.real_estate_item_missing` en la corrida AC2024/AT2025 controlada. |
| Bloqueos relacionados | `stage6.real_estate_item_missing` sigue siendo el unico bloqueo real del proof actual. Ownership y comparacion de valores quedan cubiertos por evidencia redactada y comparador ejecutado, no por el manifiesto historico aislado. |
| Politica de reanudacion | No usar `.env`, secretos, DB real, produccion, SII real, EDIG ejecutable ni integraciones externas sin autorizacion explicita. Las salidas F22/DDJJ/Balance/RLI/CPT/RAI/SAC esperadas son comparacion externa read-only, nunca input de calculo. |
| Siguiente accion | Ejecutar validaciones proporcionales del bridge, actualizar evidencia, PR/CI/merge y limpiar `stage6-mirror-proof-evidence-bridge`; despues corregir `stage6.real_estate_item_missing` usando el paquete `real_estate` controlado ya detectado, sin abrir SII real ni usar outputs esperados como input. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
