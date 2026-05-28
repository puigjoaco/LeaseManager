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
| Frente activo | Etapa 1 / Contratos - redaccion y validacion de motivos contractuales sensibles. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | Motivos heredados de entrega de llaves, prorrata de terminacion anticipada, politica de renovacion y resolucion de conflicto de renovacion pueden exponerse o aceptarse sin redaccion/validacion sensible uniforme fuera del admin. |
| Motivo de prioridad | Paquete local seguro en la etapa mas baja: cierra superficie de API/snapshot/modelo para reglas contractuales ya exigidas por la stage card sin depender de secretos, `.env`, datos reales ni integraciones. |
| Worktree | `D:/Proyectos/LeaseManager-stage1-contract-motive-redaction`. |
| Rama | `codex/stage1-contract-motive-redaction`. |
| Estado | Abierto para validar/redactar motivos contractuales sensibles, cubrir tests y evidencia. |
| Gate esperado | Tests focales de Contratos/Etapa 1, suite impactada Contratos + auditor Etapa 1, `manage.py check`, migraciones dry-run, readiness local Etapa 1, frontend build/lint, acceptance local, higiene repo y CI remoto. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Sin bloqueo externo nuevo. |
| Politica de reanudacion | Continuar este worktree hasta PR/CI/merge o pausar explicitamente aqui si aparece un bloqueo real. |
| Siguiente accion | Implementar validacion/redaccion, actualizar stage card/trazabilidad/evidencia y cerrar paquete. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
