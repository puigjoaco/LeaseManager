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
| Frente activo | Etapa 2 / Canales - alineacion de recordatorios de cobranza con mensaje saliente. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | `NotificacionCobranzaProgramada` puede enlazar un `MensajeSaliente` sin contrato o de otro arrendatario, dejando un recordatorio preparado con traza no alineada al pago mensual. |
| Motivo de prioridad | Siguiente paquete local seguro de Canales segun orden de construccion y trazabilidad: cerrar consistencia interna de recordatorios sin enviar Email/WhatsApp ni usar proveedores externos. |
| Worktree | `D:/Proyectos/LeaseManager-stage2-notification-message-alignment`. |
| Rama | `codex/stage2-notification-message-alignment`. |
| Estado | Paquete abierto; pendiente implementar guard de dominio, tests, readiness/documentacion y validaciones proporcionales. |
| Gate esperado | Stage 2 readiness local debe seguir `classification=parcial`, bloqueando snapshots heredados con recordatorios preparados cuyo mensaje no pertenezca al pago/contrato/arrendatario. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Sin bloqueo externo nuevo. |
| Politica de reanudacion | Continuar este worktree hasta commit, PR, CI, merge y limpieza; no abrir otro frente salvo instruccion explicita o pausa registrada. |
| Siguiente accion | Implementar validacion de alineacion `notificacion -> mensaje -> pago/contrato/arrendatario`, cubrir con tests focales y actualizar evidencia/trazabilidad. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
