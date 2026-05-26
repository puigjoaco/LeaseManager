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
| Frente activo | Ninguno abierto en `main`; ultimo paquete cerrado: Etapa 7 - referencias finales sensibles en readiness Reporting. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | Ninguna pendiente en cursor. El ultimo paquete hizo que `audit_stage7_reporting_readiness` clasifique explicitamente refs finales sensibles de ProcesoRentaAnual, DDJJ y F22 sin exponer valores. |
| Motivo de prioridad | El paquete cerro un diagnostico de readiness Reporting para impedir referencias finales sensibles diluidas como validacion generica. |
| Worktree | Ninguno tactico activo. |
| Rama | `main`. |
| Estado | Paquete validado, integrado y worktree tactico eliminado. |
| Gate esperado | Si `main` esta limpio, elegir el siguiente frente seguro por trazabilidad y orden de construccion. No cerrar Etapa 7 sin fuente autorizada, ledger, renta anual, API/backoffice y responsables. |
| Estado al cerrar paquete | PR #347 mergeado en `main` como `890e8f0`; CI acceptance remoto OK; validacion local OK con focal 1 test, impactada 39 tests, readiness Etapa 7 parcial, frontend build, acceptance 907 tests, higiene y `git diff --check`. |
| Bloqueos relacionados | Bloqueos externos de Reporting siguen como condicion de cierre, no bloquean hardening local. |
| Politica de reanudacion | Confirmar `git status --short --branch` y `git worktree list`; si `main` esta limpio, seleccionar el siguiente frente seguro desde trazabilidad. |
| Siguiente accion | Seleccionar nuevo paquete pequeno, seguro y verificable segun cursor, PRD/stage cards, trazabilidad y bloqueos vigentes. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
