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
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | Ninguna registrada en curso. |
| Motivo de prioridad | Tomar el siguiente frente seguro desde trazabilidad y stage cards cuando se abra un nuevo paquete. |
| Worktree | N/A. |
| Rama | `main`. |
| Estado | Sin paquete tactico abierto. Ultimo paquete cerrado: admin de Cobranza bloquea borrado manual de UF, ajustes, pagos, gates, intentos WebPay, garantias, historial, repactaciones, residuales y estados de cuenta. |
| Gate esperado | El proximo paquete debe definir su gate proporcional antes de implementar. |
| Estado al cerrar paquete | CobranzaActiva/Etapa 2 permanece preparado sin cierre falso; paquete validado con focal admin Cobranza, suite Cobranza/Etapa 2, `manage.py check`, migraciones dry-run, readiness local Etapa 2, frontend build/lint, acceptance local, higiene repo y `git diff --check`. |
| Bloqueos relacionados | Sin bloqueo externo nuevo; Etapa 2 sigue sin cierre evidencial hasta fuente autorizada y pruebas externas/controladas requeridas. |
| Politica de reanudacion | Si no existe worktree tactico sucio, abrir el siguiente paquete pequeno, seguro y verificable segun trazabilidad, stage cards y orden de construccion. |
| Siguiente accion | Diagnosticar el siguiente frente seguro desde el estado real del repo. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
