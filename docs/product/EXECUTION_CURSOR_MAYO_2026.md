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
| Frente activo | Etapa 1 / Patrimonio - evidencia de representacion designada de comunidad. |
| Fuente exacta | `01_Set_Vigente/PRD_CANONICO.md` reglas de comunidades/representacion trazable, stage card Etapa 1 y matriz de trazabilidad. |
| Brecha activa | `RepresentacionComunidad` permite modo `designado`, pero no conserva evidencia formal no sensible ni el auditor Etapa 1 bloquea snapshots heredados sin esa traza. |
| Motivo de prioridad | La representacion designada soporta comunicaciones, documentos y decisiones operativas de comunidades; sin evidencia queda una brecha de trazabilidad de Patrimonio. |
| Worktree | `D:/Proyectos/LeaseManager-stage1-community-representative-evidence`. |
| Rama | `codex/stage1-community-representative-evidence`. |
| Estado | Implementado y validado localmente; pendiente PR, CI, merge y limpieza. |
| Gate esperado | Tests focales Patrimonio/API y auditor Etapa 1, suite impactada Patrimonio + Stage1, `manage.py check`, migraciones dry-run, readiness local Etapa 1, frontend build, acceptance local, CI remoto. |
| Estado al cerrar paquete | Integrar paquete por PR/CI/merge y limpiar worktree/rama; no reabrir este frente despues del merge. |
| Bloqueos relacionados | No requiere proveedores externos, datos reales, `.env`, DB historicas ni integraciones. |
| Politica de reanudacion | Si esta rama existe, terminar solo PR/CI/merge/limpieza. Si ya no existe, no reabrir este frente y seleccionar el siguiente paquete operativo desde el estado real. |
| Siguiente accion | Ejecutar higiene final, abrir PR, esperar CI, mergear y limpiar. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
