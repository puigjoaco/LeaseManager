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
| Frente activo | Etapa 3 / Conciliacion - `stage3-bank-admin-notes-redaction`. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | `MovimientoBancarioImportado.notas_admin` acepta y expone texto manual sin validacion/redaccion de referencias sensibles heredadas. |
| Motivo de prioridad | Cierra una superficie local de Etapa 3/Conciliacion en movimientos bancarios, antes de avanzar a Contabilidad. |
| Worktree | `D:/Proyectos/LeaseManager-stage3-bank-admin-notes-redaction`. |
| Rama | `codex/stage3-bank-admin-notes-redaction`. |
| Estado | Paquete abierto; implementar validacion/redaccion/readiness/documentacion y validar sin banco real, datos reales ni secretos. |
| Gate esperado | Diagnostico local Etapa 3 parcial/no evidencial; no cierra Etapa 3 sin fuente autorizada ni prueba bancaria. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Sin bloqueo externo nuevo. |
| Politica de reanudacion | Continuar este worktree hasta PR/CI/merge/limpieza o registrar pausa explicita. |
| Siguiente accion | Implementar y validar el paquete `stage3-bank-admin-notes-redaction`. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
