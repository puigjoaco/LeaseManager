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
| Frente activo | Ninguno; ultimo paquete cerrado: Etapa 2 - Cobranza/Canales: guard de `provider_payload` sensible en mensajes salientes. |
| Fuente exacta | PR #213 `Guard Stage 2 message provider payloads`; commit `51182e3`; merge `23b3f1e`; `docs/product/TRACEABILITY_MATRIX_MAYO_2026.md` fila `CobranzaActiva`; `docs/product/STAGE_CARDS/ETAPA_2_COBRANZA_CANALES.md`; `backend/canales`; `backend/core/stage2_cobranza_readiness.py`; `scripts/run-stage2-readiness-gate.ps1`. |
| Brecha activa | Cerrada localmente: `MensajeSaliente.full_clean` rechaza nuevas escrituras con `provider_payload` sensible y readiness conserva deteccion de snapshots heredados invalidos. |
| Motivo de prioridad | Paquete integrado; no hay worktree tactico abierto para este frente. |
| Worktree | Ninguno. |
| Rama | `main` sincronizada tras merge `23b3f1e`. |
| Estado | PR #213 integrado con CI `acceptance` verde; worktree `D:/Proyectos/LeaseManager-stage2-message-provider-payload-guard` eliminado y rama tactica local/remota eliminada. |
| Gate esperado | `scripts/run-stage2-readiness-gate.ps1` debe seguir en `classification=parcial`, `ready_for_stage2_cobranza=false` con fuente local; no cierra Etapa 2 sin fuente autorizada y pruebas Email/WebPay controladas. |
| Estado al cerrar paquete | `parcial`; avance local preparado, sin cierre real de Etapa 2. |
| Bloqueos relacionados | Falta fuente autorizada, Etapa 1 confirmada y pruebas externas controladas de Email/WebPay para cierre real de Etapa 2; no bloquea preparacion local. |
| Politica de reanudacion | Si `main` esta limpio y no hay worktrees tacticos sucios, seleccionar el siguiente frente util, seguro y trazable desde la matriz/PRD/arquitectura. |
| Siguiente accion | Diagnosticar el siguiente paquete local cerrable y abrir worktree `codex/...` solo si el cambio no es trivial. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
