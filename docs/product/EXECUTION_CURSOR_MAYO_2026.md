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
| Frente activo | Sin paquete tactico abierto tras cerrar Etapa 5 - contexto responsable/evidencial en aprobacion de cierre mensual. |
| Fuente exacta | `main` debe quedar limpio tras el merge del paquete; PRD vigente y stage card Etapa 5 fijan contabilidad asistida con aprobacion responsable, sin decision contable autonoma. |
| Brecha activa | Ninguna brecha tactica abierta en este cursor. |
| Motivo de prioridad | Evitar que reanudaciones reabran el paquete ya implementado: cierres mensuales aprobados conservan responsable/evidencia no sensible de la liquidacion en resumen y auditoria. |
| Worktree | N/A tras limpieza del paquete. |
| Rama | `main` tras merge y limpieza. |
| Estado | Paquete Etapa 5 approval context implementado, validado localmente y documentado; no declarar cierre de Etapa 5 sin Conciliacion cerrada, fuente `snapshot_controlado` o `real_autorizado`, ledger/reportes controlados y responsables finales. |
| Gate esperado | Para el siguiente paquete, repetir protocolo: diagnosticar desde repo limpio, elegir siguiente frente seguro por trazabilidad, usar worktree `codex/...`, validar proporcionalmente, actualizar evidencia/trazabilidad si aplica y cerrar con PR/CI/merge/limpieza. |
| Estado al cerrar paquete | `approve_monthly_close()` conserva contexto de `LiquidacionMensual` en `resumen_obligaciones`; la API audita `approved` y `state_changed` con transicion y contexto redactable; readiness detecta cierres heredados sin responsable/evidencia de aprobacion. |
| Bloqueos relacionados | Etapa 5 no cierra sin Conciliacion cerrada, fuente `snapshot_controlado` o `real_autorizado`, ledger/reportes controlados y responsables finales. Es condicion de cierre, no freno para preparar siguientes paquetes locales. |
| Politica de reanudacion | No reabrir este paquete ni redactar goals. Si `main` esta limpio, seleccionar el siguiente frente seguro desde AGENTS, PRD, matriz, stage cards y evidencia. No abrir ni usar el worktree externo con PDFs tributarios reales sin solicitud concreta del usuario. |
| Siguiente accion | Tras merge y limpieza, continuar con el siguiente frente local seguro segun orden y trazabilidad vigentes. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
