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
| Frente activo | Patrimonio / Etapa 1 - redaccion admin de evidencia de servicios de propiedad. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | `ServicioPropiedadAdmin` expone `evidencia_ref` cruda por campos admin por defecto, aunque API/snapshot ya redactan y el dominio rechaza nuevas refs sensibles. |
| Motivo de prioridad | Primer frente no cerrado en orden de construccion: Patrimonio Etapa 1; brecha local cerrable sin datos externos. |
| Worktree | `D:/Proyectos/LeaseManager-stage1-service-admin-evidence-redaction`. |
| Rama | `codex/stage1-service-admin-evidence-redaction`. |
| Estado | En implementacion. |
| Gate esperado | Validaciones focales de Patrimonio/admin, suite impactada Etapa 1, checks locales y CI remoto. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Sin bloqueo externo nuevo. |
| Politica de reanudacion | Continuar este worktree hasta PR/CI/merge/limpieza antes de abrir otro frente. |
| Siguiente accion | Cerrar exposicion admin cruda de `ServicioPropiedad.evidencia_ref`, agregar cobertura y actualizar trazabilidad/evidencia. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
