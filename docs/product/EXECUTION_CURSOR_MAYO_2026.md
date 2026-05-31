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
| Frente activo | Etapa 2 Cobranza/WebPay - auditoria atomica de preparacion de intentos. |
| Fuente exacta | Estado real de `main` en `f09e1f1`, `docs/product/STAGE_CARDS/ETAPA_2_COBRANZA_CANALES.md`, `backend/cobranza/services.py`, `backend/cobranza/views.py`, `backend/cobranza/tests.py`, readiness Etapa 2, trazabilidad, evidencia y bloqueos vigentes. |
| Brecha activa | `WebPayIntentPrepareView` crea `cobranza.webpay_intento.prepared` despues de que `prepare_webpay_intent()` ya persistio el intento. Si la auditoria falla o el servicio se invoca internamente, puede quedar un intento WebPay preparado/bloqueado sin evento atomico alineado. |
| Motivo de prioridad | Cierra una brecha local verificable de Etapa 2: WebPay debe quedar cerrado/condicionado y trazable sin llamar Transbank ni depender de integraciones externas. |
| Worktree | `D:/Proyectos/LeaseManager-stage2-webpay-prepare-audit`. |
| Rama | `codex/stage2-webpay-prepare-audit`. |
| Estado | Paquete abierto para implementacion y validacion. |
| Gate esperado | Tests focales de preparacion WebPay con auditoria de servicio y rollback ante fallo de auditoria; suite impactada `cobranza core.tests_stage2_cobranza_readiness`; `manage.py check`; `makemigrations --check --dry-run --noinput`; readiness local Etapa 2 como parcial esperado; frontend build/lint si corresponde; acceptance local; higiene repo y `git diff --check`; CI GitHub antes de merge. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Etapa 2 sigue parcial para cierre real por fuente autorizada y pruebas Email/WebPay controladas. Este paquete no requiere `.env`, secretos, DB historica, datos reales, snapshots autorizados, backfills, deploys ni integraciones externas. |
| Politica de reanudacion | Si `git status` y `git worktree list` muestran solo `main` limpio, diagnosticar el siguiente frente seguro; si aparece un worktree sucio, terminar o pausar ese paquete antes de abrir otro frente. |
| Siguiente accion | Mover/asegurar la auditoria de preparacion WebPay dentro del servicio atomico, cubrir rollback e idempotencia local, y validar. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
