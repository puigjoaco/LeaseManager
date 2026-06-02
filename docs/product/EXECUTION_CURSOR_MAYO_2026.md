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
| Frente activo | Reporting / Etapa 7. |
| Fuente exacta | Estado real de `main` en `c0697a5` despues de PR #627, stage card Etapa 7, readiness Reporting y trazabilidad vigente. |
| Brecha activa | La API de resumen tributario anual debe bloquear `ProcesoRentaAnual` final sin `paquete_ddjj_ref`/`borrador_f22_ref` trazable o con referencias sensibles, alineada con readiness Etapa 7. |
| Motivo de prioridad | Reporting es el siguiente frente seguro por orden arquitectonico; la brecha es local, verificable y no requiere secretos, datos reales ni integraciones externas. |
| Worktree | `D:/Proyectos/LeaseManager-reporting-annual-process-refs`. |
| Rama | `codex/reporting-annual-process-refs`. |
| Estado | Paquete tactico validado localmente; pendiente PR, CI remoto, merge y limpieza. |
| Gate esperado | Focal Reporting anual, suite impactada `reporting core.tests_stage7_reporting_readiness core.tests_stage6_renta_anual_readiness`, `manage.py check`, `makemigrations --check --dry-run`, gate Etapa 7 local, frontend build/lint si aplica, acceptance local, higiene y CI remoto. |
| Estado al cerrar paquete | Pendiente. Al cerrar, registrar PR/merge, limpiar worktree/rama y volver el cursor a `Ninguno` desde `main` sincronizado. |
| Bloqueos relacionados | Los cierres evidenciales que dependan de fuentes externas siguen condicionados por autorizacion/fuente controlada y no bloquean trabajo local seguro. |
| Politica de reanudacion | Si no hay worktree tactico abierto, diagnosticar desde `main` limpio y elegir el siguiente frente util por orden de construccion, trazabilidad, stage cards y evidencia vigente. |
| Siguiente accion | Confirmar `git status --short --branch` y `git worktree list`; luego elegir el siguiente paquete pequeno, local, verificable y cerrable. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
