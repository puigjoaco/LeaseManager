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
| Frente activo | Etapa 2 - Cobranza/Canales: guard de `provider_payload` sensible en mensajes salientes. |
| Fuente exacta | `docs/product/TRACEABILITY_MATRIX_MAYO_2026.md` fila `CobranzaActiva`; `docs/product/STAGE_CARDS/ETAPA_2_COBRANZA_CANALES.md`; `backend/canales`; `backend/core/stage2_cobranza_readiness.py`; `scripts/run-stage2-readiness-gate.ps1`. |
| Brecha activa | `MensajeSaliente` redacta y readiness detecta `provider_payload` sensible heredado, pero el modelo no rechaza escrituras nuevas con URLs, tokens, credenciales o correos en ese payload. |
| Motivo de prioridad | Brecha local segura de Etapa 2: evita que Canales persista nuevos payloads sensibles sin abrir Email, WhatsApp ni proveedores externos. |
| Worktree | `D:/Proyectos/LeaseManager-stage2-message-provider-payload-guard`. |
| Rama | `codex/stage2-message-provider-payload-guard`. |
| Estado | Paquete tactico abierto desde `main` limpio en `8589c38`; implementacion y validacion en curso. |
| Gate esperado | `scripts/run-stage2-readiness-gate.ps1` debe seguir en `classification=parcial`, `ready_for_stage2_cobranza=false` con fuente local; no cierra Etapa 2 sin fuente autorizada y pruebas Email/WebPay controladas. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Falta fuente autorizada, Etapa 1 confirmada y pruebas externas controladas de Email/WebPay para cierre real de Etapa 2; no bloquea preparacion local. |
| Politica de reanudacion | Continuar este paquete desde el worktree indicado; si esta cerrado, volver a `main` limpio y seleccionar el siguiente frente trazable. |
| Siguiente accion | Implementar, validar, actualizar evidencia/trazabilidad/stage card, empaquetar PR, esperar CI, mergear y limpiar worktree/rama. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
