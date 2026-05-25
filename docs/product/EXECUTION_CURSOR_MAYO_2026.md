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
| Frente activo | Ninguno. Ultimo paquete cerrado: Etapa 2 - CobranzaActiva/WebPay, coherencia entre intento WebPay confirmado manualmente y pago mensual cerrado. |
| Fuente exacta | PR #225 `Guard Stage 2 WebPay confirmation alignment`; commit `32abb25`; merge `1e5912c`; `backend/cobranza/models.py`; `backend/core/stage2_cobranza_readiness.py`; tests de Cobranza/Etapa 2; stage card, trazabilidad y evidencia actualizadas. |
| Brecha activa | Cerrada localmente: `IntentoPagoWebPay` confirmado exige `PagoMensual` pagado y misma `fecha_pago_webpay`; readiness clasifica snapshots heredados con pago no pagado, sin fecha WebPay del pago o con fecha distinta. |
| Motivo de prioridad | Paquete local, pequeno y verificable completado sin secretos, `.env`, DB historica, datos reales ni integraciones externas. |
| Worktree | Ninguno. Solo debe quedar el worktree principal `D:/Proyectos/LeaseManager`. |
| Rama | `main`, sincronizada con `origin/main`. |
| Estado | PR #225 integrado con CI remoto verde; worktree tactico y ramas local/remota eliminados. |
| Gate esperado | Etapa 2 local queda como diagnostico parcial/no evidencial; no cierra Cobranza sin Etapa 1 evidenciada y fuente `snapshot_controlado` o `real_autorizado`. |
| Estado al cerrar paquete | Preparacion local de WebPay/Etapa 2 reforzada; cierre real de Etapa 2 sigue pendiente de fuentes/evidencias autorizadas. |
| Bloqueos relacionados | Prueba externa real/controlada de Email/WebPay y datos de Etapa 1 confirmados siguen siendo condicion de cierre, no freno para elegir otro paquete local seguro. |
| Politica de reanudacion | Si `main` esta limpio y no hay worktrees tacticos sucios, diagnosticar el siguiente paquete pequeno, trazable y local desde la matriz/stage cards. |
| Siguiente accion | Confirmar `git status --short --branch` y `git worktree list`; elegir el siguiente frente seguro por trazabilidad y abrir worktree `codex/...` solo si requiere cambios no triviales. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
