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
| Frente activo | Ninguno. Ultimo paquete cerrado: Etapa 2 - Canales, readiness operacional de mensajes salientes en dominio. |
| Fuente exacta | PR #241 `Guard outbound message operational readiness`; commit `62cf636`; merge `63450b3`; `backend/canales/models.py`; `backend/canales/services.py`; `backend/canales/tests.py`; stage card Etapa 2, trazabilidad y evidencia actualizadas. |
| Brecha activa | Cerrada localmente: `MensajeSaliente.clean()` rechaza mensajes `preparado`/`enviado` sin readiness operacional y mensajes enviados sin `external_ref` trazable no sensible. |
| Motivo de prioridad | Hardening trazable de Canales completado sin Email/WhatsApp/WebPay reales, `.env`, secretos ni datos reales. |
| Worktree | Ninguno. |
| Rama | `main` sincronizada tras PR #241. |
| Estado | Paquete integrado en main con CI verde; worktree tactico eliminado. |
| Gate esperado | Etapa 2 local queda como diagnostico parcial/no evidencial; no cierra sin fuente autorizada, evidencia Etapa 1 y pruebas Email/WebPay controladas. |
| Estado al cerrar paquete | Cerrado e integrado en main con validacion local, acceptance local y CI remoto. |
| Bloqueos relacionados | Evidencia Etapa 1, prueba externa real/controlada de Email/WebPay y responsables siguen siendo condicion de cierre real de Etapa 2. |
| Politica de reanudacion | Confirmar estado real con `git status --short --branch` y `git worktree list`; si no hay worktree tactico abierto, elegir el siguiente paquete seguro por trazabilidad. |
| Siguiente accion | Seleccionar el siguiente frente util desde stage cards, matriz de trazabilidad y PRD, abrir worktree `codex/...` si corresponde y avanzar con validaciones proporcionales. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
