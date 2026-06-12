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
| Frente activo | Etapa 2 / Cobranza - refresh scoped de mora y estado de cuenta global. |
| Fuente exacta | Base `main` limpia en `8eb6d458`; paquete trabajado en worktree tactico `D:/Proyectos/LeaseManager-stage2-overdue-global-state-sync` y rama `codex/stage2-overdue-global-state-sync`; rescue pausado fuera de alcance. |
| Brecha activa | `refresh_overdue_payments()` con usuario scoped no debe dejar stale el `EstadoCuentaArrendatario` global despues de mutar pagos visibles; debe recalcular el agregado global derivado con la misma fecha de corte, sin exponer resumen monetario global en la respuesta/auditoria scoped. |
| Motivo de prioridad | Brecha local, pequena y verificable posterior al rebuild scoped: conserva la regla de no persistir resumen parcial, pero mantiene sincronizado el resumen global usado por readiness y backoffice tras una mutacion real de mora. |
| Worktree | `D:/Proyectos/LeaseManager-stage2-overdue-global-state-sync`. |
| Rama | `codex/stage2-overdue-global-state-sync`. |
| Estado | Validacion local completa del paquete Cobranza; falta PR, CI remoto, merge y limpieza. |
| Gate esperado | Gate local Etapa 2 queda `classification=parcial`, `ready_for_stage2_cobranza=false`, sin cierre evidencial falso. |
| Estado al cerrar paquete | Focal Cobranza OK; suite impactada Cobranza/readiness OK; `manage.py check` OK; migraciones dry-run OK; gate Etapa 2 parcial OK; frontend build/lint OK; acceptance local OK; faltan PR/CI/merge/limpieza. |
| Bloqueos relacionados | Los cierres evidenciales que dependan de fuentes externas siguen condicionados por autorizacion/fuente controlada y no bloquean trabajo local seguro. |
| Politica de reanudacion | Si no hay worktree tactico de producto abierto, diagnosticar desde `main` limpio y elegir el siguiente frente util por orden de construccion, trazabilidad, stage cards y evidencia vigente. El rescue pausado no habilita lectura de datos reales ni bloquea trabajo local seguro. |
| Siguiente accion | Abrir PR, esperar CI remoto, mergear, sincronizar `main` y eliminar worktree/rama tactica. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
