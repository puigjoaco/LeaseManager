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
| Frente activo | `stage6-ownership-review-checklist`. |
| Fuente exacta | worktree `D:/Proyectos/10_ACTIVOS/LeaseManager-stage6-ownership-review-checklist`, sobre `main` `0a3a2500`. |
| Brecha activa | El validador de patch ownership ya esta integrado; falta una checklist repetible, no sensible y versionable como codigo para coordinar revision/OCR legal, validacion redactada y decision de inyectar `package.ownership`. |
| Motivo de prioridad | Evita que el siguiente paso dependa de memoria del chat o de artefactos locales sueltos: enumera candidatos, paginas renderizadas, participantes pendientes, porcentaje total, redaccion de salida y readiness sin guardar nombres, RUTs, texto bruto ni rutas crudas. |
| Worktree | Continuar/cerrar `D:/Proyectos/10_ACTIVOS/LeaseManager-stage6-ownership-review-checklist`. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `codex/stage6-ownership-review-checklist`; al cerrar, PR/CI/merge y limpiar worktree. |
| Estado | `build_annual_tax_ownership_review_checklist` pasa prueba focal. Contra template/visual packet AC2024/AT2025 y patch pendiente sintetico bajo `local-evidence/`, la checklist queda `ready_for_manual_review=true`, `reviewable_candidates_total=10`, `rendered_candidates_total=10`, `ready_for_controlled_db_load=false` y `ownership_patch_missing` por `participants_count=0`. |
| Gate esperado | El paquete no completa ownership real: deja el control operativo para completar participantes con revision/OCR legal autorizada y revalidar sin exponer PII. |
| Estado al cerrar paquete | No reabrir labor source ref, bienes raices, DDJJ/F22 semantico, comparador Balance/RLI/CPT/RAI/SAC ni prompts de goal. El siguiente frente real seguira siendo completar `ownership_patch` bajo `local-evidence/` desde revision/OCR legal controlada y reauditar readiness. |
| Bloqueos relacionados | `ownership_patch_missing` y `ownership_snapshot_missing` hasta completar participantes revisados; `ownership_source_missing` en manifiesto estricto hasta convertir fuente candidata en snapshot controlado. |
| Politica de reanudacion | No usar `.env`, secretos, DB real, produccion, SII real, EDIG ejecutable ni integraciones externas sin autorizacion explicita. Las salidas F22/DDJJ/Balance/RLI/CPT/RAI/SAC esperadas son comparacion externa read-only, nunca input de calculo. |
| Siguiente accion | Ejecutar validaciones proporcionales del checklist, actualizar evidencia, PR/CI/merge y limpiar `stage6-ownership-review-checklist`; despues completar `ownership_patch` real solo desde revision/OCR legal controlada bajo `local-evidence/`. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
