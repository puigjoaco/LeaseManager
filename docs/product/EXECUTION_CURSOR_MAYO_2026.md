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
| Frente activo | Conciliacion / admin operativo de solo lectura. |
| Fuente exacta | Stage card Etapa 3, trazabilidad vigente, evidencia vigente y estado real del repositorio. |
| Brecha activa | `MovimientoBancarioImportadoAdmin`, `IngresoDesconocidoAdmin`, `CuadraturaBancariaAdmin` y `TransferenciaIntercuentaAdmin` ya eran readonly por campos, pero conservaban permiso Django admin de cambio. |
| Motivo de prioridad | Cerrar una brecha local de bypass administrativo en entidades que deben mutar por APIs o servicios auditados. |
| Worktree | `D:/Proyectos/LeaseManager-conciliacion-admin-change-guard`. |
| Rama | `codex/conciliacion-admin-change-guard`. |
| Estado | Paquete tactico validado localmente; pendiente PR, CI, merge y limpieza. |
| Gate esperado | Focal Conciliacion admin, suite Conciliacion/readiness Etapa 3, `manage.py check`, migraciones dry-run, gate local Etapa 3 parcial, frontend build/lint, acceptance local, higiene repo y `git diff --check`. |
| Estado al cerrar paquete | Validacion local OK: focal Conciliacion admin, suite Conciliacion/readiness Etapa 3, `manage.py check`, migraciones dry-run, gate local Etapa 3 parcial, frontend build/lint, acceptance local, higiene repo y `git diff --check`. |
| Bloqueos relacionados | Ninguno nuevo; Etapa 3 sigue parcial para cierre real por banco real o snapshot autorizado, pero este paquete local no depende de eso. |
| Politica de reanudacion | Si no existe worktree tactico sucio, abrir el siguiente paquete pequeno, seguro y verificable segun trazabilidad, stage cards y orden de construccion. |
| Siguiente accion | Diagnosticar el siguiente frente seguro desde el estado real del repo. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
