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
| Frente activo | Sin paquete tactico activo tras preparar codigos residuales estrictamente post-contrato. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | Ninguna fijada en cursor. |
| Motivo de prioridad | El paquete Etapa 2 / CobranzaActiva - codigos residuales post-contrato queda validado localmente para PR/CI/merge; no debe reabrirse tras integrarse. |
| Worktree | Ninguno esperado aparte del root principal cuando el paquete este mergeado y limpio. |
| Rama | Ninguna rama tactica activa esperada tras merge. |
| Estado | Listo para seleccionar el siguiente frente desde el estado real de `main`. |
| Gate esperado | Antes de abrir otro paquete, confirmar `git status --short --branch`, `git worktree list` y revisar trazabilidad/stage cards para escoger el siguiente avance local seguro. |
| Estado al cerrar paquete | El paquete no cierra Etapa 2; endurece dominio/API/readiness para que codigos residuales heredados o nuevos sean efectivamente post-contrato. |
| Bloqueos relacionados | Prueba externa real/controlada de correo/WebPay y datos Etapa 1 confirmados siguen siendo condiciones de cierre, no requisitos para este paquete local. |
| Politica de reanudacion | Si no existe worktree tactico sucio, no reconstruir tareas previas: seleccionar el siguiente paquete operativo desde el estado real de `main`. |
| Siguiente accion | Tras PR/CI/merge/limpieza del paquete, elegir el siguiente frente trazable y seguro. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
