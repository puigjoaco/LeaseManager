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
| Frente activo | `stage6-ownership-patch-validator`. |
| Fuente exacta | worktree `D:/Proyectos/10_ACTIVOS/LeaseManager-stage6-ownership-patch-validator`, sobre `main` `191ac4bd`. |
| Brecha activa | La prueba espejo AC2024/AT2025 tiene fuente reorganizada suficiente para piloto desde libros cerrados y cadena ownership con 15 candidatos, 10 revisables y 19 paginas visuales; falta validar un patch controlado de socios/participaciones antes de inyectarlo al paquete DB. |
| Motivo de prioridad | Es el puente seguro entre revision/OCR legal y `package.ownership`: evita versionar PII, rechaza refs sensibles, exige porcentajes/vigencias/RUT validos y no permite inferir socios desde F22/DDJJ/outputs finales. |
| Worktree | Continuar/cerrar `D:/Proyectos/10_ACTIVOS/LeaseManager-stage6-ownership-patch-validator`. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `codex/stage6-ownership-patch-validator`; al cerrar, PR/CI/merge y limpiar worktree. |
| Estado | `validate_annual_tax_ownership_patch` y su comando pasan pruebas focales. Contra el template real AC2024/AT2025, un patch pendiente bajo `local-evidence/` queda `ready_for_controlled_db_load=false` solo por `$.ownership.participants` vacio, con salida redactada y `template_candidates_count=10`. |
| Gate esperado | El paquete no cierra la prueba espejo: deja listo el control previo para completar ownership. El mirror proof seguira parcial hasta cargar snapshot ownership controlado, regenerar writer/mirror y revisar artefactos anuales. |
| Estado al cerrar paquete | No reabrir labor source ref, bienes raices, DDJJ/F22 semantico, comparador Balance/RLI/CPT/RAI/SAC ni prompts de goal. El siguiente frente real es completar/OCR ownership controlado y reauditar readiness del paquete. |
| Bloqueos relacionados | `ownership_patch_missing` para patch pendiente, `ownership_source_missing` en manifiesto completo y `ownership_snapshot_missing` en readiness anual hasta completar participantes revisados. |
| Politica de reanudacion | No usar `.env`, secretos, DB real, produccion, SII real, EDIG ejecutable ni integraciones externas sin autorizacion explicita. Las salidas F22/DDJJ/Balance/RLI/CPT/RAI/SAC esperadas son comparacion externa read-only, nunca input de calculo. |
| Siguiente accion | Ejecutar validaciones finales del paquete, PR/CI/merge y limpiar `stage6-ownership-patch-validator`; despues completar `ownership_patch` real solo desde revision/OCR legal controlada bajo `local-evidence/`. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
