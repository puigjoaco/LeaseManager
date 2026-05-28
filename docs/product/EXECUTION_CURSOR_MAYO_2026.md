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
| Frente activo | Conciliacion / Ingresos desconocidos - redaccion de sugerencias asistidas. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | `IngresoDesconocido.sugerencia_asistida` se expone como payload crudo en API/snapshot/admin y readiness Etapa 3 no clasifica sugerencias heredadas con claves o valores sensibles. |
| Motivo de prioridad | Frente local seguro de Etapa 3: cierra una superficie de exposicion en Conciliacion sin banco real, `.env`, datos reales, DB historicas, backfills, deploys ni integraciones externas. |
| Worktree | `D:/Proyectos/LeaseManager-stage3-unknown-income-suggestion-redaction`. |
| Rama | `codex/stage3-unknown-income-suggestion-redaction`. |
| Estado | Abierto para redactar sugerencias asistidas de ingresos desconocidos, cubrir admin/API/snapshot/readiness y actualizar trazabilidad/evidencia. |
| Gate esperado | Test focal Conciliacion/readiness, suite impactada Stage3/Conciliacion, `manage.py check`, migraciones dry-run, gate Etapa 3 local, frontend build/lint, acceptance local, higiene repo y CI remoto. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Sin bloqueo externo nuevo. |
| Politica de reanudacion | Continuar este worktree hasta PR/CI/merge o pausar explicitamente aqui si aparece un bloqueo real. |
| Siguiente accion | Redactar `sugerencia_asistida` en serializer/snapshot/admin de ingresos desconocidos, clasificar payloads sensibles en readiness y validar con pruebas proporcionales. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
