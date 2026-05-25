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
| Frente activo | Etapa 5 - Documentos PDF, politica documental activa en dominio. |
| Fuente exacta | Stage card Etapa 5 Documentos, matriz de trazabilidad Documentos, `backend/documentos/models.py`, `backend/documentos/readiness.py`. |
| Brecha activa | En curso: readiness detecta documentos sin politica activa para su tipo documental; el dominio/API debe rechazar nuevas escrituras equivalentes y evitar desactivar politicas usadas por documentos existentes. |
| Motivo de prioridad | Brecha local trazable que endurece Documentos sin leer storage real, `.env`, documentos productivos ni integraciones externas. |
| Worktree | `D:/Proyectos/LeaseManager-stage5-document-policy-domain-guard`. |
| Rama | `codex/stage5-document-policy-domain-guard`. |
| Estado | Implementacion en curso. |
| Gate esperado | Etapa 5 Documentos local queda como diagnostico parcial/no evidencial; no cierra sin fuente autorizada, politica final, PDF controlado y responsable. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Evidencia final autorizada, politica final, PDF controlado y responsable siguen siendo condicion de cierre, no requisito para este hardening local. |
| Politica de reanudacion | Confirmar estado real con `git status --short --branch` y `git worktree list`; si no hay worktree tactico abierto, elegir el siguiente paquete seguro por trazabilidad. |
| Siguiente accion | Seleccionar el siguiente frente util desde stage cards, matriz de trazabilidad y PRD, abrir worktree `codex/...` si corresponde y avanzar con validaciones proporcionales. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
