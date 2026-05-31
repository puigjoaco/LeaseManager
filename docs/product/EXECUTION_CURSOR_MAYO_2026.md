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
| Frente activo | Sin paquete tactico abierto posterior a integrar este paquete. |
| Fuente exacta | Estado real de `main` tras integrar PR #574 en `d857ff1`, PRD canonico, `docs/product/STAGE_CARDS/ETAPA_5_DOCUMENTOS_PDF.md`, trazabilidad, evidencia y bloqueos vigentes. |
| Brecha activa | Ninguna. Ultimo paquete cerrado: `DocumentoEmitido.clean()` exige `PlantillaDocumental` activa para el mismo tipo documental y version; Stage 6 quedo alineado con plantilla activa en fixture valida. |
| Motivo de prioridad | La ficha Etapa 5 exige plantilla activa para cada documento emitido y PDF generado; el paquete dejo cerrado ese guard local tambien en dominio. |
| Worktree | Ninguno tras merge. El laboratorio usado por este paquete fue `D:/Proyectos/LeaseManager-stage5-document-template-domain-guard`. |
| Rama | `main` limpio tras merge; laboratorio cerrado: `codex/stage5-document-template-domain-guard`. |
| Estado | Paquete Etapa 5 / Documentos cerrado; luego de este ajuste de cursor, queda libre para diagnosticar el siguiente frente seguro. |
| Gate esperado | No aplica a paquete cerrado. El siguiente paquete debe definir gates proporcionales antes de editar. |
| Estado al cerrar paquete | Focal 3 tests OK, suite Documentos 84 tests OK, Stage 6 focal 1 test OK, `manage.py check`, migraciones dry-run, readiness local Etapa 5 Documentos `classification=parcial`, `npm ci`, `npm run build`, `npm run lint`, acceptance local 1116 tests OK, higiene repo y `git diff --check`. |
| Bloqueos relacionados | Sin bloqueo externo nuevo. No requiere `.env`, secretos, DB historica, datos reales, snapshots autorizados, bancos reales, backfills, deploys ni integraciones externas. |
| Politica de reanudacion | Si `git status` y `git worktree list` muestran solo `main` limpio, diagnosticar el siguiente frente seguro; si aparece un worktree sucio, terminar o pausar ese paquete antes de abrir otro frente. |
| Siguiente accion | Diagnosticar el siguiente frente seguro desde el estado real del repo. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
