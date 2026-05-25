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
| Frente activo | Etapa 6 - Renta anual, referencias finales tributarias en dominio. |
| Fuente exacta | Stage cards Etapa 4/6/7, matriz de trazabilidad SII/Renta/Reporting, `backend/sii/models.py`, `backend/core/stage6_renta_anual_readiness.py`, `backend/core/stage7_reporting_readiness.py`. |
| Brecha activa | En curso: readiness detecta F29/ProcesoRentaAnual/DDJJ/F22 avanzados sin referencia final trazable; el dominio SII debe rechazar nuevas escrituras equivalentes via `full_clean()`. |
| Motivo de prioridad | Brecha local trazable que endurece SII/Renta/Reporting sin conectar SII, leer certificados, `.env`, datos reales ni integraciones externas. |
| Worktree | `D:/Proyectos/LeaseManager-stage6-annual-ref-domain-guard`. |
| Rama | `codex/stage6-annual-ref-domain-guard`. |
| Estado | Implementacion en curso. |
| Gate esperado | Etapa 6 local queda como diagnostico parcial/no evidencial; no cierra sin fuente autorizada, doce cierres/snapshot controlado, regla fiscal, respaldos y responsable tributario. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Evidencia final autorizada, SII/control fiscal y responsable siguen siendo condicion de cierre, no requisito para este hardening local. |
| Politica de reanudacion | Confirmar estado real con `git status --short --branch` y `git worktree list`; si no hay worktree tactico abierto, elegir el siguiente paquete seguro por trazabilidad. |
| Siguiente accion | Seleccionar el siguiente frente util desde stage cards, matriz de trazabilidad y PRD, abrir worktree `codex/...` si corresponde y avanzar con validaciones proporcionales. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
