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
| Frente activo | Etapa 1 / Contratos / admin contractual solo inspeccion. |
| Fuente exacta | Estado real de `main` en `cf47b4a`, PRD canonico, `docs/product/STAGE_CARDS/ETAPA_1_DATOS_REALES.md`, trazabilidad, evidencia y bloqueos vigentes. |
| Brecha activa | Admin Django de Contratos bloquea borrado manual, pero aun permite altas o ediciones manuales en entidades contractuales que deben pasar por API, estado, vigencia o flujo auditado. |
| Motivo de prioridad | Es la siguiente brecha local verificable de Etapa 1 despues de Patrimonio y Operacion: evita mutaciones contractuales fuera de APIs, validaciones de dominio y eventos auditables. |
| Worktree | `D:/Proyectos/LeaseManager-stage1-contracts-admin-readonly`. |
| Rama | `codex/stage1-contracts-admin-readonly`. |
| Estado | Validado localmente; pendiente PR, CI remoto, merge y limpieza. |
| Gate esperado | Focal de admins Contratos, suite Contratos/Etapa 1, `manage.py check`, migraciones dry-run, readiness local Etapa 1, frontend build/lint si aplica, acceptance local, higiene repo y CI remoto. |
| Estado al cerrar paquete | Focal Contratos admin 3 tests OK; suite Contratos/Etapa 1 253 tests OK; `manage.py check` OK; migraciones dry-run sin cambios; readiness local Etapa 1 diagnostico OK; `npm ci`, `npm run build`, `npm run lint` OK; acceptance local 1116 tests OK. |
| Bloqueos relacionados | Sin bloqueo externo nuevo. No requiere `.env`, secretos, DB historica, datos reales, snapshots autorizados, backfills, deploys ni integraciones externas. |
| Politica de reanudacion | Si existe este worktree, continuar este paquete antes de abrir otro frente. Si desaparece tras merge, diagnosticar el siguiente frente seguro desde el estado real del repo. |
| Siguiente accion | Ejecutar higiene final, crear PR, esperar CI, mergear y limpiar worktree/ramas. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
