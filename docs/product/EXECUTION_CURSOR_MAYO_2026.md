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
| Frente activo | Etapa 3 - Banco y conciliacion. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | Resoluciones manuales de ingreso desconocido y cargo bancario validan evidencia no sensible, pero sus criterios y motivos pueden aceptar o conservar texto heredado sensible sin clasificacion readiness especifica. |
| Motivo de prioridad | Completar la politica de contexto no sensible en resoluciones manuales que alimentan conciliacion y hechos contables. |
| Worktree | `D:/Proyectos/LeaseManager-stage3-manual-resolution-context-safety`. |
| Rama | `codex/stage3-manual-resolution-context-safety`. |
| Estado | Validado localmente; pendiente PR, CI, merge y limpieza. |
| Gate esperado | Etapa 3 local debe seguir como diagnostico parcial: `classification=parcial`, `ready_for_stage3_conciliacion=false`, sin fuente bancaria autorizada. |
| Estado al cerrar paquete | Focal 7 tests OK; suite impactada 120 tests OK; `manage.py check`, `makemigrations --check --dry-run`, gate local Etapa 3 `classification=parcial`, `npm ci`, `npm run build`, `npm run lint`, acceptance local 971 tests OK, higiene repo y `git diff --check` OK; CI GitHub pendiente. |
| Bloqueos relacionados | Sin bloqueo externo nuevo. |
| Politica de reanudacion | Continuar este worktree hasta validar, integrar y limpiar; no abrir otro frente mientras siga activo. |
| Siguiente accion | Ejecutar higiene final, abrir PR, esperar CI, mergear y limpiar worktree. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
