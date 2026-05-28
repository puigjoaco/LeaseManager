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
| Frente activo | Etapa 2 / CobranzaActiva - estado de cuenta solo lectura en admin. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | `EstadoCuentaArrendatarioAdmin` expone `resumen_operativo` y `score_pago` como campos editables, aunque ambos deben salir del rebuild de estado de cuenta. |
| Motivo de prioridad | Cierra la superficie admin que quedo abierta despues de hacer `score_pago` rebuild-only por API. |
| Worktree | `D:/Proyectos/LeaseManager-stage2-account-state-admin-readonly`. |
| Rama | `codex/stage2-account-state-admin-readonly`. |
| Estado | Paquete abierto. |
| Gate esperado | Etapa 2 local debe seguir `classification=parcial`, `ready_for_stage2_cobranza=false` sin Email/WebPay reales. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Sin bloqueo externo nuevo. |
| Politica de reanudacion | Continuar este worktree hasta cerrar PR o pausar aqui explicitamente. |
| Siguiente accion | Convertir resumen/score de estado de cuenta en solo lectura admin, cubrir tests, evidencia y trazabilidad. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
