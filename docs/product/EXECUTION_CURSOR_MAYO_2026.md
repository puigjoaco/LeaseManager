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
| Frente activo | Etapa 2 - Canales, contexto de auditoria de mensajes enviados. |
| Fuente exacta | PRD `EventoAuditable`; stage card Etapa 2; matriz de trazabilidad CobranzaActiva; `backend/core/stage2_cobranza_readiness.py`; `backend/core/tests_stage2_cobranza_readiness.py`; `backend/canales/tests.py`. |
| Brecha activa | En curso: readiness debe bloquear eventos auditables de mensajes `enviado` que existan pero no tengan actor o `external_ref` no sensible alineado al mensaje. |
| Motivo de prioridad | Hardening local de trazabilidad de Canales sin Email/WhatsApp/WebPay reales, `.env`, secretos ni datos reales. |
| Worktree | `D:/Proyectos/LeaseManager-stage2-sent-message-audit-context`. |
| Rama | `codex/stage2-sent-message-audit-context`. |
| Estado | En implementacion y validacion local. |
| Gate esperado | Etapa 2 local queda como diagnostico parcial/no evidencial; no cierra sin fuente autorizada, evidencia Etapa 1 y pruebas Email/WebPay controladas. |
| Estado al cerrar paquete | Pendiente de validacion, PR, CI, merge y limpieza. |
| Bloqueos relacionados | Evidencia Etapa 1, prueba externa real/controlada de Email/WebPay y responsables siguen siendo condicion de cierre real de Etapa 2. |
| Politica de reanudacion | Confirmar estado real con `git status --short --branch` y `git worktree list`; si no hay worktree tactico abierto, elegir el siguiente paquete seguro por trazabilidad. |
| Siguiente accion | Implementar deteccion de eventos de envio manual incompletos, validar Etapa 2/Canales, abrir PR, esperar CI, mergear, limpiar worktree y cerrar cursor. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
