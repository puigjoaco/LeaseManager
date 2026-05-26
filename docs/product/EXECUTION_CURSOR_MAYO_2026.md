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
| Frente activo | Etapa Documentos / PDF canonico generado por sistema. |
| Fuente exacta | `docs/product/STAGE_CARDS/ETAPA_5_DOCUMENTOS_PDF.md`; `docs/AUDITORIA_PRODUCTO_ARQUITECTURA_MAYO_2026.md` matriz por modulo Documentos. |
| Brecha activa | Falta flujo local para emitir PDF canonico generado por sistema con checksum/storage_ref derivados del contenido, sin depender de storage real. |
| Motivo de prioridad | Brecha local trazable de Documentos que prepara cierre sin usar secretos, datos reales ni integraciones externas. |
| Worktree | `D:/Proyectos/LeaseManager-stage5-document-generated-pdf`. |
| Rama | `codex/stage5-document-generated-pdf`. |
| Estado | Paquete tactico abierto. |
| Gate esperado | Tests focales Documentos/readiness, `manage.py check`, migraciones dry-run, gate documental local, frontend build y acceptance si el impacto lo justifica. |
| Estado al cerrar paquete | PR #299 mergeado en `main` con merge `68ccf49`; CI `acceptance` pass; cursor quedo sin paquete abierto. |
| Bloqueos relacionados | Fuente `snapshot_controlado` o `real_autorizado` sigue siendo condicion de cierre real de Etapa 1, no de preparacion local. |
| Politica de reanudacion | Confirmar estado real con `git status --short --branch` y `git worktree list`; si no hay worktree tactico abierto, elegir el siguiente paquete seguro por trazabilidad. |
| Siguiente accion | Implementar emision PDF generada por sistema, validar checksum/storage_ref/auditoria/readiness, actualizar trazabilidad/evidencia y cerrar con PR/CI/merge/limpieza. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
