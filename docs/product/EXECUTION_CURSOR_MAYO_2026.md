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
| Frente activo | `stage6-ddjj-media-layouts`. |
| Fuente exacta | `main` en `b211290a`, posterior al merge de PR #840. |
| Brecha activa | Etapa 6 necesita declarar formularios DDJJ aplicables con medio SII, vencimiento, layout/certificado, fuente oficial/experta y campos propios antes de tratar la matriz DDJJ/F22 como trazable. |
| Motivo de prioridad | `RENTA_ANUAL_OFFICIAL_SOURCE_GAPS_AT2026.md` deja `stage6-ddjj-official-media-layouts` como siguiente avance recomendado despues de materializar balance/RLI/CPT; es preparacion local revisable, no presentacion SII. |
| Worktree | `D:/Proyectos/LeaseManager-stage6-ddjj-media-layouts`. |
| Rama | `codex/stage6-ddjj-media-layouts`. |
| Estado | Paquete implementado localmente; pendiente validacion final, PR, CI, merge y limpieza. |
| Gate esperado | Mantener `classification=parcial`; no cerrar Etapa 6 ni presentar DDJJ/F22 sin fuente final, certificacion/formato, responsable, autorizacion y evidencia no sensible. |
| Estado al cerrar paquete | Commit, PR, CI, merge y limpieza; main debe quedar sincronizado y sin worktree tactico. |
| Bloqueos relacionados | DDJJ/F22 final sigue bloqueado sin medios/formato/certificacion SII vigentes, responsable y autorizacion explicita. |
| Politica de reanudacion | Continuar este worktree hasta cerrar, pausar explicitamente o limpiar; no reabrir goal prompts ni EDIG. |
| Siguiente accion | Ejecutar validacion final proporcional, registrar evidencia, abrir PR, esperar CI, mergear y limpiar worktree tactico. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
