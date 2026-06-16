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
| Frente activo | `ac2024-controlled-stage6-closeout`. |
| Fuente exacta | `main` posterior a PR #856, a `build_annual_tax_ownership_evidence_chain` y al paquete AC2024 de selector anual, ownership, respaldo tributario y bienes raices controlados. |
| Brecha activa | El tramo local controlado Inmobiliaria Puig AC2024/AT2025 queda resuelto en arquitectura: contabilidad mensual, ownership, bienes raices/contribuciones, respaldo tributario PDF, DDJJ/F22, matriz, dossier, export y checklist se generan desde snapshot controlado sin SII real ni outputs finales como input. |
| Motivo de prioridad | Evita reabrir ciclos ya cerrados y deja la siguiente decision reducida a revision responsable/fuente autorizada o al proximo frente trazable desbloqueado. |
| Worktree | Ningun worktree tactico debe quedar activo despues del merge de este paquete. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `main` despues del merge. Para el siguiente paquete no trivial abrir worktree hermano `codex/...` desde `main` limpio. |
| Estado | Auditor empresa/ano disponible por CLI y Reporting; candidatos empresa/ano disponibles. Para Inmobiliaria Puig AC2024/AT2025 estan integrados manifiesto read-only, cadena reproducible de ownership, plan de carga, template, auditor de paquete, draft de valores, writer DB local, run anual controlado, comparador de cobertura/identidad/valores/semantica DDJJ/F22, respaldo tributario PDF y carga `real_estate` controlada. Balance, RLI/CPT/RAI, DDJJ y F22 finales siguen como comparacion, no calculo. La corrida local ignorada `ac2024_real_estate_patch_v1.sqlite3` confirma writer con 12 meses, 1 participante y 1 propiedad/contribucion; mirror con source bundle `snapshot_controlado`; y gate Etapa 6 `classification=resuelto_confirmado`, `ready_for_stage6_renta_anual=true`, sin issues. Esto no es presentacion SII real ni calculo tributario final. |
| Gate esperado | Para repetir la evidencia, rehidratar la cadena bajo `local-evidence/`, completar solo snapshots controlados con fuente suficiente, aplicar writer/mirror contra DB local/controlada autorizada y ejecutar `audit_stage6_renta_anual_readiness --source-kind snapshot_controlado --fail-on-attention` con refs no sensibles. |
| Estado al cerrar paquete | No reabrir selector anual, ownership, respaldo tributario, bienes raices, DDJJ/F22 semantico, Balance General, RLI/CPT/RAI/SAC, EDIG ni prompts de goal como bloqueo general salvo bug nuevo. |
| Bloqueos relacionados | Sin autorizacion o fuente real no se debe presentar SII, declarar calculo tributario final ni afirmar cierre productivo. El bloqueo externo queda como condicion de cierre real/productivo, no como freno para seguir por el siguiente frente seguro. |
| Politica de reanudacion | No reabrir goal prompts, EDIG ni paquetes mergeados. No usar `.env`, secretos, DB real, produccion, SII real ni integraciones externas sin autorizacion explicita. Si falta fuente externa, continuar con preparacion local segura y trazable. |
| Siguiente accion | Tras merge/limpieza, continuar con el siguiente frente trazable desbloqueado desde `main` limpio, o pedir una unica autorizacion concreta si el usuario quiere convertir esta prueba controlada en revision con fuente real/autorizada. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
