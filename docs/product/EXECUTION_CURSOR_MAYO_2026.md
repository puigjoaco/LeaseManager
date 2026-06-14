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
| Frente activo | `stage6-real-estate-contribution-source`. |
| Fuente exacta | `main` en `226bf65`, posterior al merge de PR #842. |
| Brecha activa | Etapa 6 necesita distinguir bienes raices/arriendos preparados localmente de contribuciones/codigos F22 respaldados por fuente oficial/experta. |
| Motivo de prioridad | `RENTA_ANUAL_OFFICIAL_SOURCE_GAPS_AT2026.md` deja `stage6-real-estate-official-source` como siguiente avance recomendado despues de materializar DDJJ por medio/layout. |
| Worktree | `D:/Proyectos/LeaseManager-stage6-real-estate-contribution-source`. |
| Rama | `codex/stage6-real-estate-contribution-source`. |
| Estado | Implementado y validado localmente; pendiente commit, PR, CI, merge y limpieza. |
| Gate esperado | `scripts/run-stage6-readiness-gate.ps1` queda en `classification=parcial`; no cierra Etapa 6 ni presenta DDJJ/F22 sin fuente final, certificacion/formato, responsable, autorizacion y evidencia no sensible. |
| Estado al cerrar paquete | Commit, PR, CI, merge y limpieza; main debe quedar sincronizado y sin worktree tactico de este frente. |
| Bloqueos relacionados | Contribuciones/codigos F22 finales siguen bloqueados sin fuente SII/experta vigente, responsable y autorizacion explicita. |
| Politica de reanudacion | Continuar este worktree hasta cerrar, pausar explicitamente o limpiar; no reabrir goal prompts ni EDIG. |
| Siguiente accion | Empaquetar este frente con commit, PR, CI, merge y limpieza; despues reanudar desde `main` limpio con el siguiente paquete seguro de Etapa 6. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
