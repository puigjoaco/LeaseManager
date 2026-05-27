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
| Frente activo | Patrimonio, bloqueo de reescritura directa de participaciones. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | Empresas/comunidades existentes pueden recibir `participaciones` por update generico; el serializer borra y recrea filas, saltando el flujo auditado de transferencia patrimonial. |
| Motivo de prioridad | Frente temprano del orden de construccion; protege historia patrimonial y evita perder evidencia sin datos reales ni integraciones externas. |
| Worktree | `D:/Proyectos/LeaseManager-stage1-owner-participation-rewrite-guard`. |
| Rama | `codex/stage1-owner-participation-rewrite-guard`. |
| Estado | En desarrollo. |
| Gate esperado | Focal Patrimonio, suite Patrimonio + auditor Etapa 1, `manage.py check`, migraciones dry-run, gate Etapa 1 local, frontend build/lint, acceptance, higiene y diff-check. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Ningun bloqueo externo nuevo; Etapa 1 no queda cerrada sin fuente autorizada/snapshot controlado. |
| Politica de reanudacion | Si no hay worktree tactico sucio, seleccionar el siguiente paquete pequeno, seguro y trazable desde el estado real del repo. |
| Siguiente accion | Bloquear updates genericos de participaciones en owners existentes, mantener create inicial y flujo `participaciones/transferir/`, validar y cerrar PR. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
