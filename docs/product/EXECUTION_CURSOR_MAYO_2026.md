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
| Frente activo | Etapa 5 / Contabilidad - unicidad efectiva de eventos contables contabilizados. |
| Fuente exacta | `01_Set_Vigente/PRD_CANONICO.md` regla "Un mismo hecho economico no puede generar doble contabilizacion efectiva para la misma empresa, cuenta y periodo", stage card Etapa 5 y matriz de trazabilidad. |
| Brecha activa | `EventoContable` impide duplicados por `idempotency_key`, pero un snapshot o flujo directo podria dejar dos eventos `contabilizado` para la misma empresa, tipo y entidad origen si usan keys distintas. |
| Motivo de prioridad | Evita doble contabilizacion efectiva antes del cierre mensual y fortalece readiness sin depender de banco real, SII, datos reales ni secretos. |
| Worktree | `D:/Proyectos/LeaseManager-stage5-accounting-event-deduplication`. |
| Rama | `codex/stage5-accounting-event-deduplication`. |
| Estado | Implementado y validado localmente; pendiente PR, CI, merge y limpieza. |
| Gate esperado | Tests focales Contabilidad/API y readiness Etapa 5, suite impactada Contabilidad + Stage5, `manage.py check`, migraciones dry-run, readiness local Etapa 5, frontend build, acceptance local, CI remoto. |
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
