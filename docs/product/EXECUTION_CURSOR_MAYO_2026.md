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
| Frente activo | Sin worktree tactico activo; ultimo paquete cerrado: Etapa 5 - Documentos, auditoria de PDF generado y preview alineada con contenido emitido. |
| Fuente exacta | Estado real del repositorio, este cursor, `AGENTS.md`, PRD canonico, matriz de gates, stage cards, trazabilidad y evidencia vigentes. |
| Brecha activa | Ninguna brecha abierta en curso. El paquete #361 cerro la regla local: PDF generado y preview registran actor y metadata alineada, y readiness detecta eventos heredados sin actor o desalineados. |
| Motivo de prioridad | Paquete cerrado por trazabilidad documental local, sin storage real ni integraciones externas. |
| Worktree | Ninguno; solo debe existir el worktree principal despues de limpiar `D:/Proyectos/LeaseManager-document-generated-pdf-audit-alignment`. |
| Rama | `main`. |
| Estado | Paquete #361 validado, integrado y limpiado. |
| Gate esperado | Para el siguiente paquete: diagnosticar desde trazabilidad y ejecutar validaciones proporcionales. |
| Estado al cerrar paquete | PR #361 mergeado en `main` con merge commit `3126db4`; CI acceptance remoto OK. |
| Bloqueos relacionados | Ningun bloqueo externo nuevo; no cierra Documentos sin fuente autorizada/prueba PDF controlada. |
| Politica de reanudacion | Si no hay worktree tactico sucio, seleccionar el siguiente paquete pequeno, seguro y trazable desde el estado real del repo. |
| Siguiente accion | Confirmar `main` limpio y elegir el proximo frente desbloqueado por trazabilidad. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.
