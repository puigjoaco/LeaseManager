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
| Frente activo | Etapa 5 / Contabilidad - alineacion de eventos contables de transferencias intercuenta. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | `audit_stage5_contabilidad_readiness` comprobaba existencia de eventos contables de transferencia intercuenta, pero no que coincidieran con fecha, moneda y monto del movimiento bancario correspondiente. |
| Motivo de prioridad | Continuidad directa de la traza Conciliacion -> Contabilidad: Etapa 3 ya exige metadata/eventos alineados en resoluciones manuales; Etapa 5 debe bloquear snapshots de ledger con eventos de transferencia desalineados. |
| Worktree | `D:/Proyectos/LeaseManager-stage5-transfer-event-alignment`. |
| Rama | `codex/stage5-transfer-event-alignment`. |
| Estado | Paquete abierto en implementacion local. |
| Gate esperado | Readiness Etapa 5 local debe permanecer `classification=parcial`, `ready_for_stage5_contabilidad=false` por fuente local no autorizada, y bloquear transferencias con eventos contables desalineados como `stage5.internal_transfer_accounting_event_missing`. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Sin bloqueo externo nuevo. |
| Politica de reanudacion | Continuar este worktree hasta validacion, PR, CI, merge y limpieza; no abrir otro frente mientras este paquete este sucio. |
| Siguiente accion | Ejecutar pruebas focales e impactadas, gate Etapa 5 local, acceptance local, higiene, PR/CI/merge y cierre del cursor. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
