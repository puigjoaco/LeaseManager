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
| Frente activo | Etapa 2 / Cobranza - rebuild scoped de estado de cuenta. |
| Fuente exacta | Base `main` limpia en `18f6bc46`; paquete trabajado en worktree tactico `D:/Proyectos/LeaseManager-stage2-account-state-scoped-rebuild` y rama `codex/stage2-account-state-scoped-rebuild`; rescue pausado fuera de alcance. |
| Brecha activa | `rebuild_account_state()` no debe crear ni sobrescribir `EstadoCuentaArrendatario` global con un resumen parcial cuando el usuario tiene scope restringido. |
| Motivo de prioridad | Brecha local, pequena y verificable en Cobranza: evita que una vista parcial contamine el resumen operativo usado por readiness y backoffice global. |
| Worktree | `D:/Proyectos/LeaseManager-stage2-account-state-scoped-rebuild`. |
| Rama | `codex/stage2-account-state-scoped-rebuild`. |
| Estado | Validacion local completa del paquete Cobranza; falta PR, CI remoto, merge y limpieza. |
| Gate esperado | Gate local Etapa 2 queda `classification=parcial`, `ready_for_stage2_cobranza=false`, sin cierre evidencial falso. |
| Estado al cerrar paquete | Focal Cobranza OK; suite impactada Cobranza/readiness OK; `manage.py check` OK; migraciones dry-run OK; gate Etapa 2 parcial OK; frontend build/lint OK; acceptance local OK; PR/CI/merge/limpieza confirmados. |
| Bloqueos relacionados | Los cierres evidenciales que dependan de fuentes externas siguen condicionados por autorizacion/fuente controlada y no bloquean trabajo local seguro. |
| Politica de reanudacion | Si no hay worktree tactico de producto abierto, diagnosticar desde `main` limpio y elegir el siguiente frente util por orden de construccion, trazabilidad, stage cards y evidencia vigente. El rescue pausado no habilita lectura de datos reales ni bloquea trabajo local seguro. |
| Siguiente accion | Completar validaciones del paquete activo, actualizar evidencia con resultados reales, abrir PR, esperar CI, mergear, sincronizar `main` y eliminar worktree/rama tactica. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
