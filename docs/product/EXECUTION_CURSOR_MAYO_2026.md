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
| Frente activo | Compliance / auditoria historica de exportaciones sensibles. |
| Fuente exacta | Estado real de `main` en `b461a99` despues de PR #633, stage cards, trazabilidad, evidencia y bloqueos vigentes. |
| Brecha activa | Verificar y corregir falsos bloqueos de readiness cuando eventos historicos de acceso a exportaciones sensibles conservan el estado valido del momento, pero la exportacion cambia despues a revocada o expirada. |
| Motivo de prioridad | Compliance es frente temprano parcial; la brecha es local, verificable y no requiere secretos, datos reales ni fuente externa. |
| Worktree | `D:/Proyectos/LeaseManager-compliance-audit-event-state`. |
| Rama | `codex/compliance-audit-event-state`. |
| Estado | Paquete tactico abierto para confirmar la brecha con test focal, corregir readiness si aplica y cerrar con validacion proporcional. |
| Gate esperado | Test focal de readiness Compliance, suite impactada `compliance` + `core.tests_compliance_data_readiness`, `manage.py check`, `makemigrations --check --dry-run`, gate Compliance local, frontend si aplica, acceptance local, higiene, diff-check y CI. |
| Estado al cerrar paquete | Pendiente. |
| Bloqueos relacionados | Cierre evidencial de Compliance sigue condicionado por fuente autorizada y referencias externas no sensibles; este paquete solo corrige preparacion local. |
| Politica de reanudacion | Si no hay worktree tactico abierto, diagnosticar desde `main` limpio y elegir el siguiente frente util por orden de construccion, trazabilidad, stage cards y evidencia vigente. |
| Siguiente accion | Confirmar `git status --short --branch` y `git worktree list`; luego elegir el siguiente paquete pequeno, local, verificable y cerrable. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
