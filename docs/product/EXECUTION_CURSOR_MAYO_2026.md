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
| Frente activo | `stage1-representation-observation-redaction`. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | `RepresentacionComunidad.observaciones` puede contener referencias sensibles heredadas y `representacion_vigente` las expone por API sin redaccion ni clasificacion especifica del auditor Etapa 1. |
| Motivo de prioridad | Patrimonio/Etapa 1 es el siguiente frente de construccion; la brecha es local, verificable y no requiere fuente externa. |
| Worktree | `D:/Proyectos/LeaseManager-stage1-representation-observation-redaction`. |
| Rama | `codex/stage1-representation-observation-redaction`. |
| Estado | Validado localmente; pendiente commit, PR, CI, merge y limpieza. |
| Gate esperado | Etapa 1 local sigue `implementado_sin_evidencia`; el paquete endurece preparacion segura sin declarar cierre. |
| Estado al cerrar paquete | Validacion local completa OK: focal 3 tests, impacto 184 tests, acceptance 1010 tests, checks backend/frontend, higiene y diff check. |
| Bloqueos relacionados | Sin bloqueo externo nuevo. |
| Politica de reanudacion | Continuar este worktree hasta validacion, PR, CI, merge y limpieza antes de abrir otro frente. |
| Siguiente accion | Crear commit y PR del paquete, esperar CI remoto, mergear y limpiar worktree tactico. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
