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
| Frente activo | CobranzaActiva / score de pago con registro operativo. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | El PRD exige que el score de pago excluya meses sin registro operativo; el calculo actual puede considerar pagos existentes cuyo vencimiento cae antes de `Contrato.fecha_registro_operativo`. |
| Motivo de prioridad | Etapa 2/CobranzaActiva es el siguiente frente local verificable tras Etapa 1 preparada; la correccion es deterministica y no requiere fuentes externas. |
| Worktree | `D:/Proyectos/LeaseManager-stage2-score-operational-record`. |
| Rama | `codex/stage2-score-operational-record`. |
| Estado | Paquete abierto para excluir pagos sin registro operativo del score y reflejarlo en readiness/evidencia. |
| Gate esperado | Focal Cobranza/readiness; suite `cobranza core.tests_stage2_cobranza_readiness`; `manage.py check`; `makemigrations --check --dry-run`; gate Etapa 2 local; frontend build/lint; acceptance; higiene repo. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Sin bloqueo externo nuevo. |
| Politica de reanudacion | Si no existe worktree tactico sucio, tomar el siguiente frente seguro desde trazabilidad y abrirlo explicitamente en este cursor. |
| Siguiente accion | Implementar y validar exclusion de pagos sin registro operativo del score de pago y del control de readiness. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
