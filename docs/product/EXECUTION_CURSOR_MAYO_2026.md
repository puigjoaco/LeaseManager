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
| Frente activo | Etapa 5 Documentos PDF - auditoria atomica de versiones correctivas. |
| Fuente exacta | Estado real de `main` en `95c273b`, `docs/product/STAGE_CARDS/ETAPA_5_DOCUMENTOS_PDF.md`, `backend/documentos/views.py`, `backend/documentos/tests.py`, trazabilidad, evidencia y bloqueos vigentes. |
| Brecha activa | La creacion generica de una version correctiva persiste el documento antes de crear la auditoria dedicada `documentos.documento_emitido.corrective_version_created`; si falla la auditoria, puede quedar un documento correctivo sin evento dedicado hasta que readiness lo detecte. |
| Motivo de prioridad | Cierra una brecha local verificable de Etapa 5 alineando version correctiva y auditoria dedicada en una misma transaccion, igual que formalizacion y PDF generado, sin usar fuentes externas. |
| Worktree | `D:/Proyectos/LeaseManager-documents-corrective-audit-atomic`. |
| Rama | `codex/documents-corrective-audit-atomic`. |
| Estado | Paquete abierto para implementacion y validacion. |
| Gate esperado | Test focal de rollback de version correctiva si falla auditoria dedicada; suite `documentos`; `manage.py check`; `makemigrations --check --dry-run --noinput`; readiness local Documentos como parcial esperado; frontend build/lint si corresponde; acceptance local; higiene repo y `git diff --check`; CI GitHub antes de merge. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Etapa 5 Documentos sigue parcial para cierre real por politica final, fuente autorizada y prueba PDF controlada. Este paquete no requiere `.env`, secretos, DB historica, datos reales, snapshots autorizados, backfills, deploys ni integraciones externas. |
| Politica de reanudacion | Si `git status` y `git worktree list` muestran solo `main` limpio, diagnosticar el siguiente frente seguro; si aparece un worktree sucio, terminar o pausar ese paquete antes de abrir otro frente. |
| Siguiente accion | Implementar la transaccion atomica y validar rollback/auditoria. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
