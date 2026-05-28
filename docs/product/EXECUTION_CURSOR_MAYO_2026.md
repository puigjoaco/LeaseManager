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
| Frente activo | Etapa 3 / Conciliacion - traza contable de transferencias internas. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | Readiness validaba metadata de resolucion manual contra `TransferenciaIntercuenta`, pero no probaba que `evento_contable_ids` y `empresa_evento_ids` correspondieran a los `EventoContable` de salida/entrada creados para el par cargo/abono. |
| Motivo de prioridad | El servicio de resolucion de transferencias internas ya genera eventos contables; el auditor debe bloquear snapshots heredados que pierdan o desalineen esa traza antes de alimentar Contabilidad. |
| Worktree | `D:/Proyectos/LeaseManager-stage3-transfer-accounting-event-trace`. |
| Rama | `codex/stage3-transfer-accounting-event-trace`. |
| Estado | En implementacion. |
| Gate esperado | Gate Etapa 3 local como diagnostico parcial; no cierre sin fuente autorizada. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Sin bloqueo externo nuevo. |
| Politica de reanudacion | Continuar este worktree si existe sucio; no abrir otro frente hasta cerrar, pausar en cursor o recibir instruccion segura. |
| Siguiente accion | Implementar validacion de eventos contables de transferencias internas y tests focales de readiness Etapa 3. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
