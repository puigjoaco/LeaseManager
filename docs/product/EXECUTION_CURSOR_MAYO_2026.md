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
| Frente activo | Ninguno. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, `CODEX_OPERATING_PROTOCOL_MAYO_2026.md`, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | Ninguna registrada en curso. |
| Motivo de prioridad | Tomar el siguiente frente seguro por trazabilidad y orden de construccion. |
| Worktree | N/A. |
| Rama | `main`. |
| Estado | Sin paquete tactico abierto. Ultimo paquete cerrado: `Empresa` no puede quedar inactiva con cuentas recaudadoras, mandatos operativos o identidades de envio activas. |
| Gate esperado | Definir segun el siguiente frente seguro. |
| Estado al cerrar paquete | Paquete `Empresa.salida_operativa_dependencias_activas` validado con focal Patrimonio/API/auditor, suite Patrimonio + Operacion + auditor Etapa 1, `manage.py check`, migraciones dry-run, readiness local Etapa 1, frontend build/lint, acceptance local, higiene repo y `git diff --check`. |
| Bloqueos relacionados | Sin bloqueo externo nuevo; Etapa 1 no se declara cerrada sin fuente `snapshot_controlado` o `real_autorizado`. |
| Politica de reanudacion | Si se reanuda con un worktree sucio, terminar o pausar ese paquete antes de abrir otro frente. |
| Siguiente accion | Diagnosticar el siguiente frente seguro desde el estado real del repo. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
