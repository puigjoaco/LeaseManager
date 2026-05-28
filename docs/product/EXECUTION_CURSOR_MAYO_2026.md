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
| Frente activo | Etapa 5 Documentos - referencias sensibles en expedientes documentales. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | `ExpedienteDocumental` valida y expone `entidad_id`/`owner_operativo` con menor proteccion que `DocumentoEmitido`; snapshots heredados pueden conservar URL, token, credencial o correo. |
| Motivo de prioridad | Etapa 5 exige referencias documentales no sensibles y redaccion defensiva en API/snapshot/backoffice/readiness antes de cierre. |
| Worktree | `D:/Proyectos/LeaseManager-stage5-document-expediente-redaction`. |
| Rama | `codex/stage5-document-expediente-redaction`. |
| Estado | Paquete abierto desde main limpio `f2f8023`; cambios pendientes de implementacion y validacion. |
| Gate esperado | `scripts/run-stage5-documents-readiness-gate.ps1` debe seguir diagnosticando `classification=parcial`, `ready_for_stage5_documents=false` por fuente local no autorizada. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Sin bloqueo externo nuevo. |
| Politica de reanudacion | Si no existe worktree tactico sucio, seleccionar el siguiente frente seguro desde estado real del repo y documentos rectores. |
| Siguiente accion | Endurecer validacion/redaccion/readiness de expedientes documentales, probar flujo API/snapshot/admin y cerrar con PR/CI/merge/limpieza. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
