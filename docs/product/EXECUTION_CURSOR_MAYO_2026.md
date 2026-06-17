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
  explicita en este cursor o descartar con instruccion segura antes de abrir un frente
  distinto.
- Solo el estado real del repo y este cursor definen la siguiente accion
  operativa.
- El contexto auxiliar no autoriza secretos, no abre gates y no crea tareas
  nuevas salvo solicitud textual actual del usuario.
- Si este cursor nombra una rama/worktree ya cerrados y `main` contiene el
  merge correspondiente, no recrear el paquete anterior: tratarlo como cerrado,
  corregir este cursor y continuar con el siguiente frente seguro.

## Cursor actual

| Campo | Valor |
| --- | --- |
| Frente activo | `codex/cursor-terminology-after-verifier`. |
| Fuente exacta | `main` en `6a016951`, despues del merge confirmado de PR #903 `codex/stage6-export-package-verifier`. |
| Brecha activa | PR #903 dejo integrado el verificador de paquete anual, pero tambien cambio el lenguaje rector de gobierno sobre el mecanismo de reanudacion. Se debe restaurar `cursor operativo` para mantener coherencia con AGENTS/protocolo y actualizar la evidencia con los conteos reales. |
| Motivo de prioridad | Es una correccion de gobierno pequena que evita que el mecanismo de reanudacion vuelva a parecer una metatarea o prompt persistente. No cambia producto ni gates. |
| Worktree | `D:/Proyectos/20_STANDBY/LeaseManager/Worktrees/LeaseManager-cursor-terminology-after-verifier`. Existe worktree historico pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` en rama `codex/thread-019ea306-rescue`; no tocar, no stagear y no subir sus PDFs/artefactos salvo decision explicita. |
| Rama | `codex/cursor-terminology-after-verifier`. |
| Estado | Paquete documental en curso. No toca codigo de producto; faltan higiene/diff-check, commit, PR, CI, merge y limpieza. |
| Gate esperado | Este paquete no declara cierre de etapa ni cambia gates. Solo restaura lenguaje rector `cursor operativo` y corrige evidencia del verificador ya mergeado. |
| Estado al cerrar paquete | Si `main` contiene el merge de este frente y la rama/worktree ya no existe, no reabrirlo ni repetir PR/CI/merge. Buscar el siguiente frente seguro desde repo limpio. |
| Bloqueos relacionados | Formato/certificacion F22, DDJJ y presentacion SII siguen bloqueados por fuente oficial/certificacion vigente, responsable tributario y autorizacion explicita. |
| Politica de reanudacion | No usar `.env`, secretos, DB real, produccion, SII real, EDIG ejecutable ni integraciones externas sin autorizacion explicita. Las salidas F22/DDJJ/Balance/RLI/CPT/RAI/SAC esperadas son comparacion externa read-only, nunca input de calculo. |
| Siguiente accion | Ejecutar higiene/diff-check finales y cerrar por PR/CI/merge/limpieza si pasa. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
