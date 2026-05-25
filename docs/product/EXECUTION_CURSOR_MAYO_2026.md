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
| Frente activo | Etapa 2 - CobranzaActiva/WebPay: coherencia entre intento WebPay confirmado manualmente y pago mensual cerrado. |
| Fuente exacta | `docs/product/TRACEABILITY_MATRIX_MAYO_2026.md` fila `CobranzaActiva`; `docs/product/STAGE_CARDS/ETAPA_2_COBRANZA_CANALES.md`; `backend/cobranza/models.py`; `backend/cobranza/services.py`; `backend/core/stage2_cobranza_readiness.py`; tests de Cobranza/Etapa 2. |
| Brecha activa | El servicio confirma WebPay alineando intento y pago, pero un snapshot heredado puede conservar un `IntentoPagoWebPay` confirmado con pago no pagado, sin fecha WebPay del pago o con fecha distinta, y readiness no lo clasifica especificamente. |
| Motivo de prioridad | Es un hardening local de Etapa 2, pequeno y verificable, sin usar secretos, `.env`, DB historica, datos reales ni integraciones externas. |
| Worktree | `D:/Proyectos/LeaseManager-stage2-webpay-confirmation-alignment`. |
| Rama | `codex/stage2-webpay-confirmation-alignment`. |
| Estado | En implementacion. `main` queda limpio en `D:/Proyectos/LeaseManager`. |
| Gate esperado | Etapa 2 local diagnostica parcial/no evidencial; no cierra Cobranza sin Etapa 1 evidenciada y fuente `snapshot_controlado` o `real_autorizado`. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Prueba externa real/controlada de Email/WebPay y datos de Etapa 1 confirmados siguen siendo condicion de cierre, no freno para este paquete local. |
| Politica de reanudacion | Retomar este worktree hasta cerrar, pausar explicitamente en este cursor o limpiar con instruccion segura. |
| Siguiente accion | Agregar guard de dominio/readiness para intentos WebPay confirmados desalineados con `PagoMensual`, tests focales y validacion proporcional. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
